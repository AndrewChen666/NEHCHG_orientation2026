import base64
import hmac
import json
import time
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AuthContext:
    access_id: UUID
    session_id: UUID
    role: str
    team_id: UUID | None = None
    market_id: UUID | None = None
    display_name: str | None = None
    participant_id: UUID | None = None
    participant_no: str | None = None
    college_id: UUID | None = None
    stage_id: UUID | None = None
    stage_name: str | None = None
    available_roles: tuple[str, ...] = ()


def _encode_part(value: dict[str, object]) -> str:
    raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_part(value: str) -> dict[str, object]:
    padded = value + "=" * (-len(value) % 4)
    return json.loads(base64.urlsafe_b64decode(padded).decode())


def create_session_token(context: AuthContext, secret: str, ttl_minutes: int) -> str:
    payload = {
        "sub": str(context.access_id),
        "sid": str(context.session_id),
        "role": context.role,
        "team_id": str(context.team_id) if context.team_id else None,
        "market_id": str(context.market_id) if context.market_id else None,
        "name": context.display_name,
        "participant_id": str(context.participant_id) if context.participant_id else None,
        "participant_no": context.participant_no,
        "college_id": str(context.college_id) if context.college_id else None,
        "stage_id": str(context.stage_id) if context.stage_id else None,
        "stage_name": context.stage_name,
        "roles": list(context.available_roles),
        "exp": int(time.time()) + ttl_minutes * 60,
    }
    body = _encode_part(payload)
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{base64.urlsafe_b64encode(signature).decode().rstrip('=')}"


def decode_session_token(token: str, secret: str) -> AuthContext:
    try:
        body, encoded_signature = token.split(".", 1)
        expected_signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
        padded_signature = encoded_signature + "=" * (-len(encoded_signature) % 4)
        actual_signature = base64.urlsafe_b64decode(padded_signature)
        if not hmac.compare_digest(expected_signature, actual_signature):
            raise ValueError("signature")
        payload = _decode_part(body)
        if int(payload["exp"]) < int(time.time()):
            raise ValueError("expired")
        return AuthContext(
            access_id=UUID(str(payload["sub"])),
            session_id=UUID(str(payload["sid"])),
            role=str(payload["role"]),
            team_id=UUID(str(payload["team_id"])) if payload.get("team_id") else None,
            market_id=UUID(str(payload["market_id"])) if payload.get("market_id") else None,
            display_name=str(payload["name"]) if payload.get("name") else None,
            participant_id=UUID(str(payload["participant_id"])) if payload.get("participant_id") else None,
            participant_no=str(payload["participant_no"]) if payload.get("participant_no") else None,
            college_id=UUID(str(payload["college_id"])) if payload.get("college_id") else None,
            stage_id=UUID(str(payload["stage_id"])) if payload.get("stage_id") else None,
            stage_name=str(payload["stage_name"]) if payload.get("stage_name") else None,
            available_roles=tuple(str(role) for role in payload.get("roles", []) if role),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid session token") from exc
