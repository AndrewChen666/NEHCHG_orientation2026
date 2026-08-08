from asyncpg import Pool
from fastapi import APIRouter, Depends, HTTPException

from ..config import Settings, get_settings
from ..db import get_pool
from ..dependencies import get_auth_context
from ..schemas import CodeLoginRequest, LoginResponse, SessionAccess
from ..security import AuthContext, create_session_token, verify_access_code

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/code-login", response_model=LoginResponse)
async def code_login(
    payload: CodeLoginRequest,
    pool: Pool = Depends(get_pool),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    rows = await pool.fetch(
        """
        SELECT id, session_id, role, team_id, market_id, display_name, code_hash
        FROM access_codes
        WHERE session_id = $1 AND active = TRUE
        """,
        payload.session_id,
    )
    row = next((candidate for candidate in rows if verify_access_code(payload.access_code, candidate["code_hash"])), None)
    if row is None:
        raise HTTPException(status_code=401, detail={"code": "CODE_INVALID", "message": "代碼錯誤或已停用。"})

    context = AuthContext(
        access_id=row["id"],
        session_id=row["session_id"],
        role=row["role"],
        team_id=row["team_id"],
        market_id=row["market_id"],
        display_name=row["display_name"],
    )
    token = create_session_token(context, settings.session_secret, settings.session_ttl_minutes)
    return LoginResponse(
        access=SessionAccess(
            access_id=context.access_id,
            session_id=context.session_id,
            role=context.role,
            team_id=context.team_id,
            market_id=context.market_id,
            display_name=context.display_name,
        ),
        token=token,
    )


@router.get("/me", response_model=SessionAccess)
async def me(context: AuthContext = Depends(get_auth_context)) -> SessionAccess:
    return SessionAccess(
        access_id=context.access_id,
        session_id=context.session_id,
        role=context.role,
        team_id=context.team_id,
        market_id=context.market_id,
        display_name=context.display_name,
    )
