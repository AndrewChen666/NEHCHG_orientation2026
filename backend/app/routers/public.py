from asyncpg import Pool
from fastapi import APIRouter, Depends

from ..db import get_pool
from ..game_config import TEAM_COUNT

router = APIRouter(prefix="/api/v1/public", tags=["public"])
PUBLIC_TEAM_COUNT = 4


@router.get("/home")
async def get_home_content(pool: Pool = Depends(get_pool)) -> dict[str, object]:
    """Return the safe, public-facing profile data for the current event home page."""
    session = await pool.fetchrow(
        """
        SELECT id, name, status, scheduled_start
        FROM game_sessions
        ORDER BY CASE status
          WHEN 'running' THEN 0
          WHEN 'scheduled' THEN 1
          WHEN 'draft' THEN 2
          WHEN 'paused' THEN 3
          ELSE 4
        END, updated_at DESC
        LIMIT 1
        """
    )
    if session is None:
        return {"session": None, "teams": []}

    teams = await pool.fetch(
        """
        SELECT number, name, english_name, icon, description, tone
        FROM teams
        WHERE session_id = $1 AND number BETWEEN 1 AND $2
        ORDER BY number
        """,
        session["id"],
        min(TEAM_COUNT, PUBLIC_TEAM_COUNT),
    )
    return {"session": dict(session), "teams": [dict(team) for team in teams]}
