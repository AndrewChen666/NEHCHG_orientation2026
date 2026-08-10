from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request

from .config import Settings, get_settings
from .db import get_pool
from .security import AuthContext, decode_session_token


async def get_auth_context(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    pool=Depends(get_pool),
) -> AuthContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED", "message": "請先使用角色代碼登入。"})
    try:
        context = decode_session_token(authorization.removeprefix("Bearer ").strip(), settings.session_secret)
        if context.participant_id is not None:
            refreshed = await _refresh_google_context(pool, context)
            if refreshed is None:
                raise HTTPException(status_code=403, detail={"code": "STAGE_ROLE_MISSING", "message": "目前階段沒有可用的活動身分。"})
            return refreshed
        return context
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"code": "AUTH_INVALID", "message": "登入已失效，請重新輸入代碼。"}) from exc


def require_roles(*allowed_roles: str) -> Callable[..., Awaitable[AuthContext]]:
    async def dependency(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if context.role not in allowed_roles:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "目前身分沒有此操作權限。"})
        return context

    return dependency


def require_session(context: AuthContext, session_id: UUID) -> None:
    if context.session_id != session_id:
        raise HTTPException(status_code=403, detail={"code": "SESSION_MISMATCH", "message": "目前登入身分不屬於這個場次。"})


async def get_event_broker(request: Request):
    return request.app.state.event_broker


async def _refresh_google_context(pool, context: AuthContext) -> AuthContext | None:
    """Resolve the actor's current stage role on every authenticated request."""
    from .activity import get_current_stage

    stage = await get_current_stage(pool, context.session_id)
    if stage is None:
        return None
    rows = await pool.fetch(
        """
        SELECT a.role, a.team_id, a.market_id, a.college_id, a.id AS assignment_id,
               p.id AS participant_id, p.participant_no, p.display_name,
               p.college_id AS participant_college_id
        FROM stage_role_assignments a
        JOIN participants p ON p.id = a.participant_id
        WHERE a.stage_id = $1 AND a.participant_id = $2 AND a.active = TRUE
        ORDER BY CASE WHEN a.role = $3 THEN 0 ELSE 1 END, a.id
        """,
        stage["id"],
        context.participant_id,
        context.role,
    )
    if not rows:
        return None
    selected = rows[0]
    roles = tuple(dict.fromkeys(str(row["role"]) for row in rows))
    actor = await pool.fetchrow(
        """
        SELECT id FROM access_codes
        WHERE session_id = $1 AND participant_id = $2 AND stage_id = $3
          AND role_assignment_id = $4 AND active = TRUE
        ORDER BY created_at DESC LIMIT 1
        """,
        context.session_id,
        context.participant_id,
        stage["id"],
        selected["assignment_id"],
    )
    if actor is None:
        return None
    return AuthContext(
        access_id=actor["id"],
        session_id=context.session_id,
        role=selected["role"],
        team_id=selected["team_id"],
        market_id=selected["market_id"],
        display_name=selected["display_name"],
        participant_id=selected["participant_id"],
        participant_no=selected["participant_no"],
        college_id=selected["participant_college_id"],
        stage_id=stage["id"],
        stage_name=stage["name"],
        available_roles=roles,
    )
