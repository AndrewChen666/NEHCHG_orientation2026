from uuid import UUID

from asyncpg import Pool
from fastapi import APIRouter, Depends, HTTPException

from ..db import get_pool
from ..activity import get_current_stage
from ..dependencies import get_auth_context, get_event_broker, require_roles, require_session
from ..game_clock import current_period, effective_elapsed_ms
from ..game_config import normalize_config, rules_for
from ..ownership import settle_ownership
from ..realtime import EventBroker
from ..schemas import ClockActionResponse, PeriodOverrideRequest, SessionSummary
from ..security import AuthContext

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _summary(row: object) -> SessionSummary:
    rules = rules_for(row["config"])
    return SessionSummary(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        scheduled_start=row["scheduled_start"],
        started_at=row["started_at"],
        current_period=current_period(row, rules),
        manual_period_override=row["manual_period_override"],
        effective_elapsed_ms=effective_elapsed_ms(row),
    )


async def _get_session(pool: Pool, session_id: UUID) -> object:
    row = await pool.fetchrow(
        """
        SELECT id, name, status, scheduled_start, started_at, paused_at,
               accumulated_pause_ms, current_period, manual_period_override, config
        FROM game_sessions WHERE id = $1
        """,
        session_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "找不到這個遊戲場次。"})
    return row


@router.get("/{session_id}/snapshot")
async def snapshot(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    require_session(context, session_id)
    row = await _get_session(pool, session_id)
    current_stage = await get_current_stage(pool, session_id)
    teams = await pool.fetch(
        """
        SELECT t.id, t.number, t.name, w.balance AS money
        FROM teams t JOIN team_wallets w ON w.team_id = t.id
        WHERE t.session_id = $1 ORDER BY t.number
        """,
        session_id,
    )
    markets = await pool.fetch(
        """
        SELECT m.id, m.code, m.name, mo.team_id AS owner_team_id
        FROM markets m
        LEFT JOIN market_ownership mo ON mo.market_id = m.id AND mo.ended_at IS NULL
        WHERE m.session_id = $1 ORDER BY m.code
        """,
        session_id,
    )
    visible_teams = teams if context.role in {"coordinator", "magic_boss"} else [team for team in teams if team["id"] == context.team_id]
    visible_markets = markets if context.role in {"coordinator", "market_master"} else markets
    return {
        "session": _summary(row),
        "current_stage": {
            "id": current_stage["id"],
            "name": current_stage["name"],
            "stage_type": current_stage["stage_type"],
            "sort_order": current_stage["sort_order"],
        } if current_stage else None,
        "active_roles": list(context.available_roles),
        "teams": [dict(item) for item in visible_teams],
        "markets": [dict(item) for item in visible_markets],
        "last_event_sequence": await pool.fetchval(
            "SELECT COALESCE(MAX(sequence), 0) FROM game_events WHERE session_id = $1", session_id
        ),
    }


@router.get("/{session_id}/config")
async def config(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    """Expose safe display and gameplay settings to every authenticated role."""
    require_session(context, session_id)
    row = await pool.fetchrow("SELECT config FROM game_sessions WHERE id = $1", session_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "找不到這個遊戲場次。"})
    safe_config = normalize_config(row["config"])
    # The coordinator's setup endpoint is the only place that needs the raw
    # uploaded image. Keep the general gameplay config lightweight for every
    # other role instead of broadcasting a multi-megabyte data URL.
    if context.role != "coordinator":
        safe_config["map"] = {"image_data_url": None, "width": None, "height": None}
    return safe_config


async def _change_status(
    session_id: UUID,
    action: str,
    pool: Pool,
    broker: EventBroker,
) -> ClockActionResponse:
    async with pool.acquire() as connection:
        async with connection.transaction():
            row = await connection.fetchrow(
                """
                SELECT id, name, status, scheduled_start, started_at, paused_at,
                       accumulated_pause_ms, current_period, manual_period_override, config
                FROM game_sessions WHERE id = $1 FOR UPDATE
                """,
                session_id,
            )
            if row is None:
                raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "找不到這個遊戲場次。"})
            updates = {
                "start": ("running", "started_at = COALESCE(started_at, NOW()), paused_at = NULL"),
                "pause": ("paused", "paused_at = COALESCE(paused_at, NOW())"),
                "resume": ("running", "accumulated_pause_ms = accumulated_pause_ms + EXTRACT(EPOCH FROM (COALESCE(paused_at, NOW()) - COALESCE(started_at, NOW()))) * 1000, paused_at = NULL"),
                "finish": ("finished", "paused_at = NULL"),
            }
            allowed_from = {
                "start": {"draft", "scheduled"},
                "pause": {"running"},
                "resume": {"paused"},
                "finish": {"running", "paused"},
            }
            if action not in updates:
                raise HTTPException(status_code=400, detail={"code": "CLOCK_ACTION_INVALID", "message": "無效的時鐘操作。"})
            if row["status"] not in allowed_from[action]:
                raise HTTPException(status_code=409, detail={"code": "CLOCK_ACTION_UNAVAILABLE", "message": "目前場次狀態不能執行這個時鐘操作。"})
            status, clause = updates[action]
            if action == "finish":
                await settle_ownership(connection, row, final=True)
                await connection.execute(
                    "UPDATE market_ownership SET ended_at = NOW(), ended_elapsed_ms = $1 WHERE session_id = $2 AND ended_at IS NULL",
                    effective_elapsed_ms(row),
                    session_id,
                )
            await connection.execute(f"UPDATE game_sessions SET status = $1, {clause}, updated_at = NOW() WHERE id = $2", status, session_id)
            updated = await connection.fetchrow(
                """
                SELECT id, name, status, scheduled_start, started_at, paused_at,
                       accumulated_pause_ms, current_period, manual_period_override, config
                FROM game_sessions WHERE id = $1
                """,
                session_id,
            )
            sequence = await connection.fetchval(
                "UPDATE game_event_counters SET next_sequence = next_sequence + 1 WHERE session_id = $1 RETURNING next_sequence - 1",
                session_id,
            )
            await connection.execute(
                "INSERT INTO game_events (session_id, sequence, event_type, payload) VALUES ($1, $2, $3, $4::jsonb)",
                session_id,
                sequence,
                f"session.{action}",
                "{}",
            )
    result = ClockActionResponse(session=_summary(updated), event_sequence=sequence)
    await broker.publish(session_id, {"sequence": sequence, "type": f"session.{action}", "payload": result.model_dump(mode="json")})
    return result


@router.post("/{session_id}/start", response_model=ClockActionResponse)
async def start(session_id: UUID, pool: Pool = Depends(get_pool), context: AuthContext = Depends(require_roles("coordinator")), broker: EventBroker = Depends(get_event_broker)) -> ClockActionResponse:
    require_session(context, session_id)
    return await _change_status(session_id, "start", pool, broker)


@router.post("/{session_id}/pause", response_model=ClockActionResponse)
async def pause(session_id: UUID, pool: Pool = Depends(get_pool), context: AuthContext = Depends(require_roles("coordinator")), broker: EventBroker = Depends(get_event_broker)) -> ClockActionResponse:
    require_session(context, session_id)
    return await _change_status(session_id, "pause", pool, broker)


@router.post("/{session_id}/resume", response_model=ClockActionResponse)
async def resume(session_id: UUID, pool: Pool = Depends(get_pool), context: AuthContext = Depends(require_roles("coordinator")), broker: EventBroker = Depends(get_event_broker)) -> ClockActionResponse:
    require_session(context, session_id)
    return await _change_status(session_id, "resume", pool, broker)


@router.post("/{session_id}/finish", response_model=ClockActionResponse)
async def finish(session_id: UUID, pool: Pool = Depends(get_pool), context: AuthContext = Depends(require_roles("coordinator")), broker: EventBroker = Depends(get_event_broker)) -> ClockActionResponse:
    require_session(context, session_id)
    return await _change_status(session_id, "finish", pool, broker)


@router.put("/{session_id}/period", response_model=ClockActionResponse)
async def set_period_override(
    session_id: UUID,
    payload: PeriodOverrideRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
    broker: EventBroker = Depends(get_event_broker),
) -> ClockActionResponse:
    """Pin a period for incident recovery, or clear the pin to resume 15-minute timing."""
    require_session(context, session_id)
    async with pool.acquire() as connection:
        async with connection.transaction():
            row = await connection.fetchrow(
                """
                SELECT id, name, status, scheduled_start, started_at, paused_at,
                       accumulated_pause_ms, current_period, manual_period_override, config
                FROM game_sessions WHERE id = $1 FOR UPDATE
                """,
                session_id,
            )
            if row is None:
                raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "找不到這個遊戲場次。"})
            if row["status"] not in {"running", "paused"}:
                raise HTTPException(status_code=409, detail={"code": "PERIOD_CONTROL_UNAVAILABLE", "message": "請先開始遊戲，才能手動切換時段。"})
            await connection.execute(
                "UPDATE game_sessions SET manual_period_override = $1, current_period = COALESCE($1, current_period), updated_at = NOW() WHERE id = $2",
                payload.period,
                session_id,
            )
            updated = await connection.fetchrow(
                """
                SELECT id, name, status, scheduled_start, started_at, paused_at,
                       accumulated_pause_ms, current_period, manual_period_override, config
                FROM game_sessions WHERE id = $1
                """,
                session_id,
            )
            sequence = await connection.fetchval(
                "UPDATE game_event_counters SET next_sequence = next_sequence + 1 WHERE session_id = $1 RETURNING next_sequence - 1",
                session_id,
            )
            await connection.execute(
                "INSERT INTO game_events (session_id, sequence, event_type, payload) VALUES ($1, $2, 'session.period_override', $3::jsonb)",
                session_id,
                sequence,
                '{"source":"coordinator"}' if payload.period is None else f'{{"period":{payload.period},"source":"coordinator"}}',
            )
    result = ClockActionResponse(session=_summary(updated), event_sequence=sequence)
    await broker.publish(session_id, {"sequence": sequence, "type": "session.period_override", "payload": result.model_dump(mode="json")})
    return result
