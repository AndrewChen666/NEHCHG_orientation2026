from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CodeLoginRequest(BaseModel):
    session_id: UUID
    access_code: str = Field(min_length=4, max_length=64)


class SessionAccess(BaseModel):
    access_id: UUID
    session_id: UUID
    role: str
    team_id: UUID | None = None
    market_id: UUID | None = None
    display_name: str | None = None


class LoginResponse(BaseModel):
    access: SessionAccess
    token: str


class SessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: str
    scheduled_start: datetime | None = None
    started_at: datetime | None = None
    current_period: int
    effective_elapsed_ms: int


class InteractionGuard(BaseModel):
    money_pouch_presented: bool
    minimum_team_present: bool


class TransactionRequest(InteractionGuard):
    market_id: UUID
    resource_type: Literal["dragon_egg", "time_device", "unicorn_blood", "basilisk_fang"]
    direction: Literal["buy", "sell"]
    idempotency_key: str = Field(min_length=8, max_length=128)


class ChallengeRequest(InteractionGuard):
    market_id: UUID
    difficulty_level: int = Field(default=1, ge=1, le=5)
    idempotency_key: str = Field(min_length=8, max_length=128)


class ChallengeResultRequest(BaseModel):
    success: bool
    note: str | None = Field(default=None, max_length=500)


class MagicChallengeRequest(InteractionGuard):
    question_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=128)


class MagicResultRequest(BaseModel):
    success: bool
    note: str | None = Field(default=None, max_length=500)


class BlackMarketDrawRequest(InteractionGuard):
    idempotency_key: str = Field(min_length=8, max_length=128)


class BlackMarketApplyRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ClockActionResponse(BaseModel):
    session: SessionSummary
    event_sequence: int | None = None
