from asyncpg import Pool
from fastapi import APIRouter, Depends, HTTPException
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from ..activity import get_current_stage
from ..config import Settings, get_settings
from ..db import get_pool
from ..dependencies import get_auth_context
from ..schemas import GoogleLoginRequest, LoginResponse, SessionAccess
from ..security import AuthContext, create_session_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _auth_response(context: AuthContext) -> SessionAccess:
    return SessionAccess(
        access_id=context.access_id,
        session_id=context.session_id,
        role=context.role,
        team_id=context.team_id,
        market_id=context.market_id,
        display_name=context.display_name,
        participant_id=context.participant_id,
        participant_no=context.participant_no,
        college_id=context.college_id,
        stage_id=context.stage_id,
        stage_name=context.stage_name,
        available_roles=list(context.available_roles),
    )


def _verify_google_credential(credential: str, settings: Settings) -> dict[str, object]:
    audiences = settings.google_client_id_list
    if not audiences:
        raise HTTPException(status_code=503, detail={"code": "GOOGLE_LOGIN_NOT_CONFIGURED", "message": "伺服器尚未設定 Google 登入。"})
    try:
        claims = id_token.verify_oauth2_token(credential, google_requests.Request(), audiences)
    except (ValueError, google_auth_exceptions.GoogleAuthError) as exc:
        raise HTTPException(status_code=401, detail={"code": "GOOGLE_TOKEN_INVALID", "message": "Google 登入驗證失敗，請重新登入。"}) from exc
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=401, detail={"code": "GOOGLE_ISSUER_INVALID", "message": "Google 登入來源無效。"})
    if claims.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail={"code": "GOOGLE_EMAIL_UNVERIFIED", "message": "Google 帳號尚未完成 email 驗證。"})
    if not claims.get("sub") or not claims.get("email"):
        raise HTTPException(status_code=401, detail={"code": "GOOGLE_IDENTITY_INCOMPLETE", "message": "Google 帳號缺少必要身分資訊。"})
    return claims


async def _ensure_participant_role(pool: Pool, session_id, participant_id, stage_id):
    assignment = await pool.fetchrow(
        """
        SELECT id, role, team_id, market_id, college_id
        FROM stage_role_assignments
        WHERE session_id = $1 AND stage_id = $2 AND participant_id = $3
          AND active = TRUE
        ORDER BY CASE WHEN role = 'participant' THEN 0 ELSE 1 END, id
        LIMIT 1
        """,
        session_id,
        stage_id,
        participant_id,
    )
    if assignment is not None:
        return assignment
    return await pool.fetchrow(
        """
        INSERT INTO stage_role_assignments (session_id, stage_id, participant_id, role, scope_type)
        VALUES ($1, $2, $3, 'participant', 'session')
        RETURNING id, role, team_id, market_id, college_id
        """,
        session_id,
        stage_id,
        participant_id,
    )


async def _ensure_google_actor(connection, session_id, stage, participant, assignment):
    actor = await connection.fetchrow(
        """
        SELECT id FROM access_codes
        WHERE session_id = $1 AND participant_id = $2 AND stage_id = $3
          AND role_assignment_id = $4 AND active = TRUE
        ORDER BY created_at DESC LIMIT 1
        """,
        session_id,
        participant["id"],
        stage["id"],
        assignment["id"],
    )
    if actor is not None:
        return actor["id"]
    return await connection.fetchval(
        """
        INSERT INTO access_codes (
          session_id, role, display_name, team_id, market_id, code_hash,
          participant_id, stage_id, role_assignment_id
        )
        VALUES ($1, $2, $3, $4, $5, 'google-only', $6, $7, $8)
        RETURNING id
        """,
        session_id,
        assignment["role"],
        f"{participant['participant_no']}・{participant['display_name']}",
        assignment["team_id"],
        assignment["market_id"],
        participant["id"],
        stage["id"],
        assignment["id"],
    )


async def _resolve_session_id(connection, requested_session_id):
    """Resolve the single application session when the client omits its UUID."""
    if requested_session_id is not None:
        return requested_session_id

    session_id = await connection.fetchval(
        "SELECT id FROM game_sessions ORDER BY created_at DESC LIMIT 1"
    )
    if session_id is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NO_GAME_SESSION", "message": "目前尚未建立活動場次。"},
        )
    return session_id


@router.post("/google", response_model=LoginResponse)
async def google_login(
    payload: GoogleLoginRequest,
    pool: Pool = Depends(get_pool),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    claims = _verify_google_credential(payload.credential, settings)
    email = str(claims["email"]).strip().lower()
    google_subject = str(claims["sub"])

    async with pool.acquire() as connection:
        async with connection.transaction():
            session_id = await _resolve_session_id(connection, payload.session_id)
            participant = await connection.fetchrow(
                """
                SELECT id, participant_no, display_name, email, google_subject, college_id, team_id
                FROM participants
                WHERE session_id = $1 AND LOWER(email) = $2 AND active = TRUE
                FOR UPDATE
                """,
                session_id,
                email,
            )
            if participant is None:
                raise HTTPException(status_code=403, detail={"code": "GOOGLE_ACCOUNT_NOT_ALLOWED", "message": "這個 Google 帳號尚未被加入本場次名單。"})
            if participant["google_subject"] and participant["google_subject"] != google_subject:
                raise HTTPException(status_code=409, detail={"code": "GOOGLE_ACCOUNT_MISMATCH", "message": "這個 email 已綁定其他 Google 帳號，請聯絡總召。"})
            if not participant["google_subject"]:
                await connection.execute(
                    "UPDATE participants SET google_subject = $1, updated_at = NOW() WHERE id = $2",
                    google_subject,
                    participant["id"],
                )
                participant = dict(participant)
                participant["google_subject"] = google_subject

            stage = await get_current_stage(connection, session_id)
            if stage is None:
                raise HTTPException(status_code=409, detail={"code": "NO_ACTIVITY_STAGE", "message": "本場次尚未建立活動階段。"})
            assignments = await connection.fetch(
                """
                SELECT id, role, team_id, market_id, college_id
                FROM stage_role_assignments
                WHERE session_id = $1 AND stage_id = $2 AND participant_id = $3 AND active = TRUE
                ORDER BY id
                """,
                session_id,
                stage["id"],
                participant["id"],
            )
            if not assignments:
                assignment = await connection.fetchrow(
                    """
                    INSERT INTO stage_role_assignments (session_id, stage_id, participant_id, role, scope_type)
                    VALUES ($1, $2, $3, 'participant', 'session')
                    RETURNING id, role, team_id, market_id, college_id
                    """,
                    session_id,
                    stage["id"],
                    participant["id"],
                )
                assignments = [assignment]
            assignment = next((item for item in assignments if item["role"] == payload.role), None) if payload.role else assignments[0]
            if assignment is None:
                raise HTTPException(status_code=403, detail={"code": "REQUESTED_ROLE_UNAVAILABLE", "message": "目前階段沒有指定的活動身分。"})

            actor_id = await _ensure_google_actor(connection, session_id, stage, participant, assignment)
            roles = tuple(dict.fromkeys(str(item["role"]) for item in assignments))
            context = AuthContext(
                access_id=actor_id,
                session_id=session_id,
                role=assignment["role"],
                team_id=assignment["team_id"],
                market_id=assignment["market_id"],
                display_name=participant["display_name"],
                participant_id=participant["id"],
                participant_no=participant["participant_no"],
                college_id=participant["college_id"],
                stage_id=stage["id"],
                stage_name=stage["name"],
                available_roles=roles,
            )
    return LoginResponse(
        access=_auth_response(context),
        token=create_session_token(context, settings.session_secret, settings.session_ttl_minutes),
    )


@router.get("/me", response_model=SessionAccess)
async def me(context: AuthContext = Depends(get_auth_context)) -> SessionAccess:
    return _auth_response(context)
