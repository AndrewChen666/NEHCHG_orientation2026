from datetime import datetime, timezone
from uuid import UUID


def effective_elapsed_ms(row: object) -> int:
    started_at = row["started_at"]
    if started_at is None:
        return 0
    end_at = row["paused_at"] or datetime.now(timezone.utc)
    pause_ms = int(row["accumulated_pause_ms"] or 0)
    return max(0, int((end_at - started_at).total_seconds() * 1000) - pause_ms)


async def get_current_stage(pool, session_id: UUID):
    session = await pool.fetchrow(
        """
        SELECT id, status, started_at, paused_at, accumulated_pause_ms, manual_stage_id
        FROM game_sessions WHERE id = $1
        """,
        session_id,
    )
    if session is None:
        return None

    stages = await pool.fetch(
        """
        SELECT id, session_id, name, stage_type, sort_order, start_offset_ms,
               duration_minutes, config, personal_multiplier, team_multiplier,
               college_multiplier
        FROM activity_stages
        WHERE session_id = $1
        ORDER BY sort_order
        """,
        session_id,
    )
    if not stages:
        return None
    if session["manual_stage_id"] is not None:
        manual = next((stage for stage in stages if stage["id"] == session["manual_stage_id"]), None)
        if manual is not None:
            return manual

    elapsed = effective_elapsed_ms(session)
    for stage in stages:
        start = int(stage["start_offset_ms"])
        end = start + int(stage["duration_minutes"]) * 60_000
        if start <= elapsed < end:
            return stage
    return stages[0] if elapsed < int(stages[0]["start_offset_ms"]) else stages[-1]


async def get_stage(pool, stage_id: UUID):
    return await pool.fetchrow(
        """
        SELECT a.*, s.status AS session_status, s.started_at, s.paused_at,
               s.accumulated_pause_ms, s.manual_stage_id
        FROM activity_stages a
        JOIN game_sessions s ON s.id = a.session_id
        WHERE a.id = $1
        """,
        stage_id,
    )


def stage_is_current(stage: object, current: object | None) -> bool:
    return current is not None and stage["id"] == current["id"]
