import base64
import hashlib
import hmac
import json
import secrets
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


def hash_access_code(code: str, salt: str | None = None) -> str:
    actual_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", code.encode(), actual_salt.encode(), 120_000).hex()
    return f"pbkdf2_sha256${actual_salt}${digest}"


def verify_access_code(code: str, encoded: str) -> bool:
    try:
        algorithm, salt, expected = encoded.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    actual = hashlib.pbkdf2_hmac("sha256", code.encode(), salt.encode(), 120_000).hex()
    return hmac.compare_digest(actual, expected)


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
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid session token") from exc

