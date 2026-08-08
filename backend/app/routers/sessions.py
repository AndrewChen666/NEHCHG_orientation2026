from datetime import datetime, timezone
from uuid import UUID

from asyncpg import Pool
from fastapi import APIRouter, Depends, HTTPException

from ..db import get_pool
from ..dependencies import get_auth_context, get_event_broker, require_roles, require_session
from ..game_config import normalize_config
from ..realtime import EventBroker
from ..schemas import ClockActionResponse, SessionSummary
from ..security import AuthContext

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _effective_elapsed_ms(row: object) -> int:
    started_at = row["started_at"]
    if started_at is None:
        return 0
    end_at = row["paused_at"] or datetime.now(timezone.utc)
    pause_ms = int(row["accumulated_pause_ms"] or 0)
    return max(0, int((end_at - started_at).total_seconds() * 1000) - pause_ms)


def _summary(row: object) -> SessionSummary:
    return SessionSummary(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        scheduled_start=row["scheduled_start"],
        started_at=row["started_at"],
        current_period=row["current_period"],
        effective_elapsed_ms=_effective_elapsed_ms(row),
    )


async def _get_session(pool: Pool, session_id: UUID) -> object:
    row = await pool.fetchrow(
        """
        SELECT id, name, status, scheduled_start, started_at, paused_at,
               accumulated_pause_ms, current_period
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
                       accumulated_pause_ms, current_period
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
            if action not in updates:
                raise HTTPException(status_code=400, detail={"code": "CLOCK_ACTION_INVALID", "message": "無效的時鐘操作。"})
            status, clause = updates[action]
            await connection.execute(f"UPDATE game_sessions SET status = $1, {clause}, updated_at = NOW() WHERE id = $2", status, session_id)
            updated = await connection.fetchrow(
                """
                SELECT id, name, status, scheduled_start, started_at, paused_at,
                       accumulated_pause_ms, current_period
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
