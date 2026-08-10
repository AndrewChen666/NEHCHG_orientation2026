import csv
import io
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Literal
from uuid import UUID

from asyncpg import Pool
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from ..activity import effective_elapsed_ms, get_current_stage, get_stage, stage_is_current
from ..db import get_pool
from ..dependencies import get_auth_context, get_event_broker, require_roles, require_session
from ..realtime import EventBroker
from ..security import AuthContext

router = APIRouter(prefix="/api/v1", tags=["orientation"])


StageType = Literal["icebreaker", "score_only", "mini_game", "magic_village", "custom"]
RoleName = Literal["coordinator", "participant", "team_facilitator", "icebreaker_facilitator", "score_keeper", "market_master", "magic_boss"]
ScopeType = Literal["session", "college", "team", "market"]
TargetType = Literal["personal", "team", "college"]


class ParticipantImportRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=2_000_000)


class StageInput(BaseModel):
    id: UUID | None = None
    name: str = Field(min_length=1, max_length=80)
    stage_type: StageType
    sort_order: int = Field(ge=1, le=999)
    start_offset_ms: int = Field(default=0, ge=0)
    duration_minutes: int = Field(ge=1, le=1_440)
    config: dict[str, object] = Field(default_factory=dict)
    personal_multiplier: float = Field(default=1, ge=0)
    team_multiplier: float = Field(default=1, ge=0)
    college_multiplier: float = Field(default=1, ge=0)


class StageBatchRequest(BaseModel):
    stages: list[StageInput] = Field(min_length=1, max_length=999)

    @model_validator(mode="after")
    def validate_order(self):
        orders = [stage.sort_order for stage in self.stages]
        if len(set(orders)) != len(orders):
            raise ValueError("活動階段順序不可重複。")
        return self


class RoleAssignmentInput(BaseModel):
    stage_id: UUID
    participant_id: UUID
    role: RoleName
    scope_type: ScopeType = "session"
    college_id: UUID | None = None
    team_id: UUID | None = None
    market_id: UUID | None = None
    active: bool = True

    @model_validator(mode="after")
    def validate_scope(self):
        values = {"college": self.college_id, "team": self.team_id, "market": self.market_id}
        if self.scope_type == "session" and any(values.values()):
            raise ValueError("場次範圍不可同時指定學院、小隊或市場。")
        if self.scope_type != "session" and values[self.scope_type] is None:
            raise ValueError(f"{self.scope_type} 範圍需要指定對應 ID。")
        return self


class RoleAssignmentBatchRequest(BaseModel):
    assignments: list[RoleAssignmentInput] = Field(default_factory=list, max_length=10_000)


class ActiveStageRequest(BaseModel):
    stage_id: UUID | None = None


class IcebreakerGroupRequest(BaseModel):
    round_number: int = Field(ge=1, le=999)
    group_number: int = Field(ge=1, le=999)
    participant_ids: list[UUID] = Field(min_length=1, max_length=100)
    round_name: str = Field(default="", max_length=80)


class ScoreEventRequest(BaseModel):
    target_type: TargetType
    target_id: UUID
    points: Decimal = Field(max_digits=12, decimal_places=2)
    note: str | None = Field(default=None, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=128)


def _error(status: int, code: str, message: str, details: dict[str, object] | None = None):
    raise HTTPException(status_code=status, detail={"code": code, "message": message, "details": details or {}})


def _stage_dict(stage: object) -> dict[str, object]:
    return {
        "id": stage["id"],
        "session_id": stage["session_id"],
        "name": stage["name"],
        "stage_type": stage["stage_type"],
        "sort_order": stage["sort_order"],
        "start_offset_ms": stage["start_offset_ms"],
        "duration_minutes": stage["duration_minutes"],
        "config": stage["config"] or {},
        "personal_multiplier": float(stage["personal_multiplier"]),
        "team_multiplier": float(stage["team_multiplier"]),
        "college_multiplier": float(stage["college_multiplier"]),
    }


def _participant_dict(row: object) -> dict[str, object]:
    return {
        "id": row["id"],
        "participant_no": row["participant_no"],
        "display_name": row["display_name"],
        "email": row["email"],
        "google_subject": bool(row["google_subject"]),
        "college_id": row["college_id"],
        "college_code": row["college_code"],
        "college_name": row["college_name"],
        "team_id": row["team_id"],
        "team_number": row["team_number"],
        "team_name": row["team_name"],
        "active": row["active"],
    }


async def _editable_session(connection, session_id: UUID):
    row = await connection.fetchrow("SELECT id, status FROM game_sessions WHERE id = $1 FOR UPDATE", session_id)
    if row is None:
        _error(404, "SESSION_NOT_FOUND", "找不到這個遊戲場次。")
    if row["status"] not in {"draft", "scheduled"}:
        _error(409, "SESSION_LOCKED", "場次開始後不能修改活動階段或身分設定。")
    return row


async def _stage_for_context(pool: Pool, stage_id: UUID, context: AuthContext, require_current: bool = True):
    stage = await get_stage(pool, stage_id)
    if stage is None or stage["session_id"] != context.session_id:
        _error(404, "STAGE_NOT_FOUND", "找不到這個活動階段。")
    current = await get_current_stage(pool, context.session_id)
    if require_current and context.role != "coordinator" and not stage_is_current(stage, current):
        _error(409, "STAGE_NOT_ACTIVE", "目前不是這個活動階段。")
    return stage


@router.get("/sessions/{session_id}/activity")
async def activity_snapshot(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    require_session(context, session_id)
    stages = await pool.fetch("SELECT * FROM activity_stages WHERE session_id = $1 ORDER BY sort_order", session_id)
    current = await get_current_stage(pool, session_id)
    session = await pool.fetchrow(
        "SELECT status, started_at, paused_at, accumulated_pause_ms FROM game_sessions WHERE id = $1",
        session_id,
    )
    return {
        "current_stage": _stage_dict(current) if current else None,
        "effective_elapsed_ms": effective_elapsed_ms(session) if session else 0,
        "stages": [_stage_dict(stage) for stage in stages],
        "active_roles": list(context.available_roles),
        "role": context.role,
    }


@router.get("/setup/sessions/{session_id}/participants")
async def list_participants(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> list[dict[str, object]]:
    require_session(context, session_id)
    rows = await pool.fetch(
        """
        SELECT p.id, p.participant_no, p.display_name, p.email, p.google_subject,
               p.college_id, c.code AS college_code, c.name AS college_name,
               p.team_id, t.number AS team_number, t.name AS team_name, p.active
        FROM participants p
        LEFT JOIN colleges c ON c.id = p.college_id
        LEFT JOIN teams t ON t.id = p.team_id
        WHERE p.session_id = $1
        ORDER BY p.participant_no
        """,
        session_id,
    )
    return [_participant_dict(row) for row in rows]


@router.get("/sessions/{session_id}/participants")
async def list_activity_participants(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator", "score_keeper", "team_facilitator", "icebreaker_facilitator")),
) -> list[dict[str, object]]:
    require_session(context, session_id)
    rows = await pool.fetch(
        """
        SELECT p.id, p.participant_no, p.display_name, p.email, p.google_subject,
               p.college_id, c.code AS college_code, c.name AS college_name,
               p.team_id, t.number AS team_number, t.name AS team_name, p.active
        FROM participants p
        LEFT JOIN colleges c ON c.id = p.college_id
        LEFT JOIN teams t ON t.id = p.team_id
        WHERE p.session_id = $1 AND p.active = TRUE
        ORDER BY p.participant_no
        """,
        session_id,
    )
    return [_participant_dict(row) for row in rows]


@router.get("/sessions/{session_id}/score-targets")
async def score_targets(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator", "score_keeper", "team_facilitator")),
) -> dict[str, list[dict[str, object]]]:
    require_session(context, session_id)
    participants = await pool.fetch(
        "SELECT id, participant_no, display_name, team_id, college_id FROM participants WHERE session_id = $1 AND active = TRUE ORDER BY participant_no",
        session_id,
    )
    teams = await pool.fetch("SELECT id, number, name FROM teams WHERE session_id = $1 ORDER BY number", session_id)
    colleges = await pool.fetch("SELECT id, code, name FROM colleges WHERE session_id = $1 ORDER BY code", session_id)
    return {
        "personal": [dict(row) for row in participants],
        "team": [dict(row) for row in teams],
        "college": [dict(row) for row in colleges],
    }


@router.post("/setup/sessions/{session_id}/participants/import")
async def import_participants(
    session_id: UUID,
    payload: ParticipantImportRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, object]:
    require_session(context, session_id)
    reader = csv.DictReader(io.StringIO(payload.csv_text.lstrip("\ufeff")))
    if not reader.fieldnames:
        _error(422, "CSV_HEADER_MISSING", "CSV 檔案缺少標題列。")
    aliases = {
        "participant_no": ("participant_no", "number", "編號", "參加者編號"),
        "display_name": ("display_name", "name", "姓名"),
        "email": ("email", "Google email", "google_email", "信箱", "電子郵件"),
        "college_code": ("college_code", "college", "學院代碼", "學院"),
        "college_name": ("college_name", "學院名稱"),
        "team_number": ("team_number", "team", "小隊", "小隊編號"),
    }
    normalized_headers = {header.strip().lower(): header for header in reader.fieldnames if header}

    def value(row: dict[str, str], key: str) -> str:
        for alias in aliases[key]:
            actual = normalized_headers.get(alias.lower())
            if actual is not None:
                return (row.get(actual) or "").strip()
        return ""

    rows: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    seen_nos: set[str] = set()
    seen_emails: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        participant_no = value(row, "participant_no")
        display_name = value(row, "display_name")
        email = value(row, "email").lower()
        college_code = value(row, "college_code")
        college_name = value(row, "college_name") or college_code
        team_raw = value(row, "team_number")
        team_match = re.search(r"\d+", team_raw)
        team_number = int(team_match.group()) if team_match else None
        row_errors: list[str] = []
        if not participant_no:
            row_errors.append("缺少參加者編號")
        if not display_name:
            row_errors.append("缺少姓名")
        if "@" not in email:
            row_errors.append("email 格式不正確")
        if participant_no in seen_nos:
            row_errors.append("CSV 內有重複編號")
        if email in seen_emails:
            row_errors.append("CSV 內有重複 email")
        seen_nos.add(participant_no)
        seen_emails.add(email)
        if row_errors:
            errors.append({"row": row_number, "errors": row_errors})
        rows.append({
            "participant_no": participant_no,
            "display_name": display_name,
            "email": email,
            "college_code": college_code,
            "college_name": college_name,
            "team_number": team_number,
            "row": row_number,
        })
    if errors:
        _error(422, "CSV_INVALID", "CSV 名單有資料錯誤，尚未匯入。", {"rows": errors})

    async with pool.acquire() as connection:
        async with connection.transaction():
            team_rows = await connection.fetch("SELECT id, number, name FROM teams WHERE session_id = $1", session_id)
            teams = {int(row["number"]): row for row in team_rows}
            existing_emails = await connection.fetch(
                "SELECT id, LOWER(email) AS email, participant_no FROM participants WHERE session_id = $1",
                session_id,
            )
            email_owner = {row["email"]: row for row in existing_emails}
            for item in rows:
                if item["team_number"] is not None and item["team_number"] not in teams:
                    _error(422, "TEAM_NOT_FOUND", f"第 {item['row']} 列的小隊不存在。")
                owner = email_owner.get(item["email"])
                if owner is not None and owner["participant_no"] != item["participant_no"]:
                    _error(422, "EMAIL_ALREADY_USED", f"第 {item['row']} 列的 email 已被其他編號使用。")

            created = 0
            updated = 0
            for item in rows:
                college_id = None
                if item["college_code"]:
                    college_id = await connection.fetchval(
                        """
                        INSERT INTO colleges (session_id, code, name) VALUES ($1, $2, $3)
                        ON CONFLICT (session_id, code) DO UPDATE SET name = EXCLUDED.name
                        RETURNING id
                        """,
                        session_id,
                        item["college_code"],
                        item["college_name"],
                    )
                team_id = teams[item["team_number"]]["id"] if item["team_number"] is not None else None
                existing = await connection.fetchrow(
                    "SELECT id, google_subject FROM participants WHERE session_id = $1 AND participant_no = $2 FOR UPDATE",
                    session_id,
                    item["participant_no"],
                )
                if existing is None:
                    await connection.execute(
                        """
                        INSERT INTO participants (session_id, participant_no, display_name, email, college_id, team_id)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        session_id,
                        item["participant_no"],
                        item["display_name"],
                        item["email"],
                        college_id,
                        team_id,
                    )
                    created += 1
                else:
                    await connection.execute(
                        """
                        UPDATE participants
                        SET display_name = $1, email = $2, college_id = $3, team_id = $4, updated_at = NOW()
                        WHERE id = $5
                        """,
                        item["display_name"],
                        item["email"],
                        college_id,
                        team_id,
                        existing["id"],
                    )
                    updated += 1
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, payload) VALUES ($1, $2, 'participants.import', $3::jsonb)",
                session_id,
                context.access_id,
                json.dumps({"created": created, "updated": updated}),
            )
    return {"created": created, "updated": updated, "total": len(rows)}


@router.get("/setup/sessions/{session_id}/stages")
async def list_stages(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> list[dict[str, object]]:
    require_session(context, session_id)
    rows = await pool.fetch("SELECT * FROM activity_stages WHERE session_id = $1 ORDER BY sort_order", session_id)
    return [_stage_dict(row) for row in rows]


@router.put("/setup/sessions/{session_id}/stages")
async def replace_stages(
    session_id: UUID,
    payload: StageBatchRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, object]:
    require_session(context, session_id)
    async with pool.acquire() as connection:
        async with connection.transaction():
            await _editable_session(connection, session_id)
            existing = await connection.fetch("SELECT id FROM activity_stages WHERE session_id = $1", session_id)
            existing_ids = {row["id"] for row in existing}
            submitted_ids = {stage.id for stage in payload.stages if stage.id is not None}
            unknown_ids = submitted_ids - existing_ids
            if unknown_ids:
                _error(422, "STAGE_SESSION_MISMATCH", "活動階段不屬於這個場次。")
            removed_ids = existing_ids - submitted_ids
            if removed_ids:
                dependent = await connection.fetchval(
                    """
                    SELECT EXISTS(SELECT 1 FROM stage_role_assignments WHERE stage_id = ANY($1::uuid[]))
                        OR EXISTS(SELECT 1 FROM score_events WHERE stage_id = ANY($1::uuid[]))
                        OR EXISTS(SELECT 1 FROM icebreaker_rounds WHERE stage_id = ANY($1::uuid[]))
                    """,
                    list(removed_ids),
                )
                if dependent:
                    _error(409, "STAGE_HAS_DATA", "已有資料的活動階段不能刪除。")
                await connection.execute("DELETE FROM activity_stages WHERE id = ANY($1::uuid[])", list(removed_ids))
            await connection.execute("UPDATE activity_stages SET sort_order = sort_order + 100000 WHERE session_id = $1", session_id)
            stage_ids: list[UUID] = []
            for item in payload.stages:
                if item.id is None:
                    stage_id = await connection.fetchval(
                        """
                        INSERT INTO activity_stages (session_id, name, stage_type, sort_order, start_offset_ms, duration_minutes, config, personal_multiplier, team_multiplier, college_multiplier)
                        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10) RETURNING id
                        """,
                        session_id, item.name, item.stage_type, item.sort_order, item.start_offset_ms,
                        item.duration_minutes, json.dumps(item.config), item.personal_multiplier, item.team_multiplier, item.college_multiplier,
                    )
                else:
                    stage_id = item.id
                    await connection.execute(
                        """
                        UPDATE activity_stages
                        SET name = $1, stage_type = $2, sort_order = $3, start_offset_ms = $4,
                            duration_minutes = $5, config = $6::jsonb, personal_multiplier = $7,
                            team_multiplier = $8, college_multiplier = $9, updated_at = NOW()
                        WHERE id = $10 AND session_id = $11
                        """,
                        item.name, item.stage_type, item.sort_order, item.start_offset_ms,
                        item.duration_minutes, json.dumps(item.config), item.personal_multiplier,
                        item.team_multiplier, item.college_multiplier, stage_id, session_id,
                    )
                stage_ids.append(stage_id)
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, payload) VALUES ($1, $2, 'stages.replace', $3::jsonb)",
                session_id,
                context.access_id,
                json.dumps({"count": len(stage_ids)}),
            )
    return {"updated": len(payload.stages)}


@router.put("/sessions/{session_id}/active-stage")
async def set_active_stage(
    session_id: UUID,
    payload: ActiveStageRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, object]:
    require_session(context, session_id)
    if payload.stage_id is not None:
        stage = await get_stage(pool, payload.stage_id)
        if stage is None or stage["session_id"] != session_id:
            _error(404, "STAGE_NOT_FOUND", "找不到要切換的活動階段。")
    await pool.execute("UPDATE game_sessions SET manual_stage_id = $1, updated_at = NOW() WHERE id = $2", payload.stage_id, session_id)
    return {"stage_id": payload.stage_id}


@router.get("/setup/sessions/{session_id}/role-assignments")
async def list_role_assignments(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> list[dict[str, object]]:
    require_session(context, session_id)
    rows = await pool.fetch(
        """
        SELECT a.id, a.stage_id, s.name AS stage_name, a.participant_id,
               p.participant_no, p.display_name, a.role, a.scope_type,
               a.college_id, a.team_id, a.market_id, a.active
        FROM stage_role_assignments a
        JOIN activity_stages s ON s.id = a.stage_id
        JOIN participants p ON p.id = a.participant_id
        WHERE a.session_id = $1
        ORDER BY s.sort_order, p.participant_no, a.role
        """,
        session_id,
    )
    return [dict(row) for row in rows]


@router.put("/setup/sessions/{session_id}/role-assignments")
async def replace_role_assignments(
    session_id: UUID,
    payload: RoleAssignmentBatchRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, object]:
    require_session(context, session_id)
    async with pool.acquire() as connection:
        async with connection.transaction():
            await _editable_session(connection, session_id)
            stage_ids = {row["id"] for row in await connection.fetch("SELECT id FROM activity_stages WHERE session_id = $1", session_id)}
            participant_ids = {row["id"] for row in await connection.fetch("SELECT id FROM participants WHERE session_id = $1", session_id)}
            for assignment in payload.assignments:
                if assignment.stage_id not in stage_ids or assignment.participant_id not in participant_ids:
                    _error(422, "ASSIGNMENT_SCOPE_INVALID", "角色指派的階段或參加者不屬於這個場次。")
            await connection.execute("DELETE FROM stage_role_assignments WHERE session_id = $1", session_id)
            for assignment in payload.assignments:
                await connection.execute(
                    """
                    INSERT INTO stage_role_assignments (session_id, stage_id, participant_id, role, scope_type, scope_id, college_id, team_id, market_id, active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    session_id,
                    assignment.stage_id,
                    assignment.participant_id,
                    assignment.role,
                    assignment.scope_type,
                    assignment.college_id or assignment.team_id or assignment.market_id,
                    assignment.college_id,
                    assignment.team_id,
                    assignment.market_id,
                    assignment.active,
                )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, payload) VALUES ($1, $2, 'role_assignments.replace', $3::jsonb)",
                session_id,
                context.access_id,
                json.dumps({"count": len(payload.assignments)}),
            )
    return {"updated": len(payload.assignments)}


async def _assert_activity_operator(pool: Pool, stage_id: UUID, context: AuthContext):
    stage = await _stage_for_context(pool, stage_id, context)
    if context.role not in {"coordinator", "icebreaker_facilitator", "team_facilitator"}:
        _error(403, "ICEBREAKER_ROLE_REQUIRED", "只有隊輔或總召可以記錄破冰分圈。")
    if stage["stage_type"] != "icebreaker":
        _error(409, "STAGE_TYPE_INVALID", "目前階段不是破冰活動。")
    return stage


async def _pair_counts(pool: Pool, stage_id: UUID, round_number: int, participant_ids: list[UUID]) -> dict[UUID, int]:
    if not participant_ids:
        return {}
    rows = await pool.fetch(
        """
        SELECT a.participant_id AS left_id, b.participant_id AS right_id
        FROM icebreaker_group_members a
        JOIN icebreaker_group_members b ON b.group_id = a.group_id AND b.participant_id <> a.participant_id
        JOIN icebreaker_rounds r ON r.id = a.round_id
        WHERE r.stage_id = $1 AND r.round_number < $2
        """,
        stage_id,
        round_number,
    )
    requested = set(participant_ids)
    counts: Counter[UUID] = Counter()
    for row in rows:
        if row["left_id"] in requested:
            counts[row["right_id"]] += 1
        if row["right_id"] in requested:
            counts[row["left_id"]] += 1
    return dict(counts)


@router.post("/stages/{stage_id}/icebreaker/groups")
async def save_icebreaker_group(
    stage_id: UUID,
    payload: IcebreakerGroupRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    await _assert_activity_operator(pool, stage_id, context)
    if len(set(payload.participant_ids)) != len(payload.participant_ids):
        _error(422, "PARTICIPANT_DUPLICATE", "同一圈不可重複加入同一位參加者。")
    async with pool.acquire() as connection:
        async with connection.transaction():
            participant_rows = await connection.fetch(
                "SELECT id, participant_no, display_name FROM participants WHERE session_id = $1 AND id = ANY($2::uuid[]) AND active = TRUE",
                context.session_id,
                payload.participant_ids,
            )
            if len(participant_rows) != len(payload.participant_ids):
                _error(422, "PARTICIPANT_NOT_FOUND", "圈圈中包含不存在或已停用的參加者。")
            round_row = await connection.fetchrow(
                """
                INSERT INTO icebreaker_rounds (session_id, stage_id, round_number, name, created_by)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (stage_id, round_number) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                context.session_id,
                stage_id,
                payload.round_number,
                payload.round_name,
                context.access_id,
            )
            group_row = await connection.fetchrow(
                """
                INSERT INTO icebreaker_groups (session_id, round_id, group_number, created_by)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (round_id, group_number) DO UPDATE SET created_by = EXCLUDED.created_by
                RETURNING id
                """,
                context.session_id,
                round_row["id"],
                payload.group_number,
                context.access_id,
            )
            conflict = await connection.fetchval(
                """
                SELECT EXISTS(
                  SELECT 1 FROM icebreaker_group_members
                  WHERE round_id = $1 AND participant_id = ANY($2::uuid[]) AND group_id <> $3
                )
                """,
                round_row["id"],
                payload.participant_ids,
                group_row["id"],
            )
            if conflict:
                _error(409, "PARTICIPANT_IN_OTHER_GROUP", "這一輪已有參加者被記錄在其他圈圈。")
            await connection.execute(
                "DELETE FROM icebreaker_group_members WHERE group_id = $1 AND NOT (participant_id = ANY($2::uuid[]))",
                group_row["id"],
                payload.participant_ids,
            )
            for participant_id in payload.participant_ids:
                await connection.execute(
                    """
                    INSERT INTO icebreaker_group_members (session_id, round_id, group_id, participant_id)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (group_id, participant_id) DO NOTHING
                    """,
                    context.session_id,
                    round_row["id"],
                    group_row["id"],
                    participant_id,
                )
            members = await connection.fetch(
                """
                SELECT p.id, p.participant_no, p.display_name
                FROM icebreaker_group_members m JOIN participants p ON p.id = m.participant_id
                WHERE m.group_id = $1 ORDER BY p.participant_no
                """,
                group_row["id"],
            )
    pair_counts = await _pair_counts(pool, stage_id, payload.round_number, payload.participant_ids)
    warnings = [{"participant_id": item["id"], "shared_count": pair_counts.get(item["id"], 0)} for item in members if pair_counts.get(item["id"], 0)]
    return {"round_number": payload.round_number, "group_number": payload.group_number, "members": [dict(item) for item in members], "warnings": warnings}


@router.get("/stages/{stage_id}/icebreaker/recommendations")
async def icebreaker_recommendations(
    stage_id: UUID,
    round_number: int = Query(ge=1, le=999),
    group_number: int | None = Query(default=None, ge=1, le=999),
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(get_auth_context),
) -> list[dict[str, object]]:
    await _assert_activity_operator(pool, stage_id, context)
    current_members: list[UUID] = []
    if group_number is not None:
        current_members = list(await pool.fetchval(
            """
            SELECT COALESCE(array_agg(participant_id), ARRAY[]::uuid[])
            FROM icebreaker_group_members m JOIN icebreaker_rounds r ON r.id = m.round_id
            JOIN icebreaker_groups g ON g.id = m.group_id
            WHERE r.stage_id = $1 AND r.round_number = $2 AND g.group_number = $3
            """,
            stage_id,
            round_number,
            group_number,
        ) or [])
    current_round_ids = set(await pool.fetchval(
        """
        SELECT COALESCE(array_agg(m.participant_id), ARRAY[]::uuid[])
        FROM icebreaker_group_members m JOIN icebreaker_rounds r ON r.id = m.round_id
        WHERE r.stage_id = $1 AND r.round_number = $2
        """,
        stage_id,
        round_number,
    ) or [])
    participants = await pool.fetch(
        "SELECT id, participant_no, display_name, team_id, college_id FROM participants WHERE session_id = $1 AND active = TRUE ORDER BY participant_no",
        context.session_id,
    )
    counts = await _pair_counts(pool, stage_id, round_number, current_members)
    return [
        {
            "id": item["id"],
            "participant_no": item["participant_no"],
            "display_name": item["display_name"],
            "shared_count": counts.get(item["id"], 0),
            "never_shared": counts.get(item["id"], 0) == 0,
        }
        for item in participants
        if item["id"] not in current_members and item["id"] not in current_round_ids
    ]


def _target_is_allowed(context: AuthContext, target_type: str, target: object) -> bool:
    if context.role in {"coordinator", "score_keeper"}:
        if context.role == "coordinator" or context.team_id is None and context.college_id is None:
            return True
    if context.role == "team_facilitator" or context.role == "score_keeper":
        if target_type == "personal":
            return target["team_id"] == context.team_id
        if target_type == "team":
            return target["id"] == context.team_id
        if target_type == "college":
            return context.college_id is not None and target["id"] == context.college_id
    return False


async def _resolve_score_target(connection, session_id: UUID, payload: ScoreEventRequest):
    queries = {
        "personal": "SELECT id, team_id, college_id FROM participants WHERE id = $1 AND session_id = $2 AND active = TRUE",
        "team": "SELECT id FROM teams WHERE id = $1 AND session_id = $2",
        "college": "SELECT id FROM colleges WHERE id = $1 AND session_id = $2",
    }
    target = await connection.fetchrow(queries[payload.target_type], payload.target_id, session_id)
    if target is None:
        _error(404, "SCORE_TARGET_NOT_FOUND", "找不到指定的計分對象。")
    return target


@router.post("/stages/{stage_id}/scores")
async def record_score(
    stage_id: UUID,
    payload: ScoreEventRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(get_auth_context),
    broker: EventBroker = Depends(get_event_broker),
) -> dict[str, object]:
    stage = await _stage_for_context(pool, stage_id, context)
    if context.role not in {"coordinator", "score_keeper", "team_facilitator"}:
        _error(403, "SCORE_ROLE_REQUIRED", "目前身分不能記錄分數。")
    if stage["stage_type"] not in {"score_only", "mini_game", "custom", "icebreaker"} and context.role != "coordinator":
        _error(409, "SCORING_NOT_AVAILABLE", "目前階段未開放現場計分。")
    async with pool.acquire() as connection:
        async with connection.transaction():
            existing = await connection.fetchrow(
                "SELECT id, points, target_type, target_id FROM score_events WHERE session_id = $1 AND idempotency_key = $2",
                context.session_id,
                payload.idempotency_key,
            )
            if existing:
                return {"id": existing["id"], "points": float(existing["points"]), "target_type": existing["target_type"], "target_id": existing["target_id"], "replayed": True}
            target = await _resolve_score_target(connection, context.session_id, payload)
            if not _target_is_allowed(context, payload.target_type, target):
                _error(403, "SCORE_SCOPE_INVALID", "目前身分不能替這個對象加分。")
            score_id = await connection.fetchval(
                """
                INSERT INTO score_events (session_id, stage_id, target_type, target_id, points, note, idempotency_key, recorded_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id
                """,
                context.session_id,
                stage_id,
                payload.target_type,
                payload.target_id,
                payload.points,
                payload.note,
                payload.idempotency_key,
                context.access_id,
            )
            sequence = await connection.fetchval(
                "UPDATE game_event_counters SET next_sequence = next_sequence + 1 WHERE session_id = $1 RETURNING next_sequence - 1",
                context.session_id,
            )
            await connection.execute(
                "INSERT INTO game_events (session_id, sequence, event_type, payload) VALUES ($1, $2, 'score.created', $3::jsonb)",
                context.session_id,
                sequence,
                json.dumps({"stage_id": str(stage_id), "target_type": payload.target_type, "target_id": str(payload.target_id), "points": float(payload.points)}),
            )
    await broker.publish(context.session_id, {"sequence": sequence, "type": "score.created", "payload": {"stage_id": str(stage_id), "target_type": payload.target_type, "target_id": str(payload.target_id), "points": float(payload.points)}})
    return {"id": score_id, "points": float(payload.points), "target_type": payload.target_type, "target_id": payload.target_id, "event_sequence": sequence, "replayed": False}


async def _leaderboard(pool: Pool, session_id: UUID, target_type: str, stage_id: UUID | None):
    params: list[object] = [session_id, target_type]
    stage_clause = ""
    if stage_id is not None:
        stage_clause = " AND e.stage_id = $3"
        params.append(stage_id)
    rows = await pool.fetch(
        f"""
        SELECT e.target_id,
               COALESCE(SUM(e.points), 0) AS raw_points,
               COALESCE(SUM(e.points * CASE e.target_type
                 WHEN 'personal' THEN s.personal_multiplier
                 WHEN 'team' THEN s.team_multiplier
                 ELSE s.college_multiplier END), 0) AS weighted_points
        FROM score_events e JOIN activity_stages s ON s.id = e.stage_id
        WHERE e.session_id = $1 AND e.target_type = $2{stage_clause}
        GROUP BY e.target_id
        ORDER BY weighted_points DESC, raw_points DESC, e.target_id
        """,
        *params,
    )
    if target_type == "personal":
        labels = await pool.fetch("SELECT id, participant_no, display_name FROM participants WHERE session_id = $1", session_id)
        label_map = {row["id"]: {"participant_no": row["participant_no"], "name": row["display_name"]} for row in labels}
    elif target_type == "team":
        labels = await pool.fetch("SELECT id, number, name FROM teams WHERE session_id = $1", session_id)
        label_map = {row["id"]: {"number": row["number"], "name": row["name"]} for row in labels}
    else:
        labels = await pool.fetch("SELECT id, code, name FROM colleges WHERE session_id = $1", session_id)
        label_map = {row["id"]: {"code": row["code"], "name": row["name"]} for row in labels}
    return [
        {
            "target_id": row["target_id"],
            **label_map.get(row["target_id"], {"name": "未知對象"}),
            "raw_points": float(row["raw_points"]),
            "weighted_points": float(row["weighted_points"]),
        }
        for row in rows
    ]


@router.get("/sessions/{session_id}/leaderboards")
async def leaderboards(
    session_id: UUID,
    stage_id: UUID | None = Query(default=None),
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    require_session(context, session_id)
    if stage_id is not None:
        stage = await get_stage(pool, stage_id)
        if stage is None or stage["session_id"] != session_id:
            _error(404, "STAGE_NOT_FOUND", "找不到指定的活動階段。")
    return {
        "stage_id": stage_id,
        "personal": await _leaderboard(pool, session_id, "personal", stage_id),
        "team": await _leaderboard(pool, session_id, "team", stage_id),
        "college": await _leaderboard(pool, session_id, "college", stage_id),
    }
