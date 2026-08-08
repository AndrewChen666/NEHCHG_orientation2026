from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request

from .config import Settings, get_settings
from .security import AuthContext, decode_session_token


async def get_auth_context(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED", "message": "請先使用角色代碼登入。"})
    try:
        return decode_session_token(authorization.removeprefix("Bearer ").strip(), settings.session_secret)
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
