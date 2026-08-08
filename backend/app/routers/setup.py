import json
import secrets
from datetime import datetime
from typing import Literal
from uuid import UUID

from asyncpg import Pool
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, model_validator

from ..config import Settings, get_settings
from ..db import get_pool
from ..dependencies import require_roles, require_session
from ..security import AuthContext, hash_access_code

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

RESOURCE_TYPES = ("dragon_egg", "time_device", "unicorn_blood", "basilisk_fang")
MARKET_CODES = tuple("ABCDEFGH")
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class InventorySeed(BaseModel):
    dragon_egg: int = Field(default=0, ge=0)
    time_device: int = Field(default=0, ge=0)
    unicorn_blood: int = Field(default=0, ge=0)
    basilisk_fang: int = Field(default=0, ge=0)

    def as_dict(self) -> dict[str, int]:
        return self.model_dump()


class TeamSeed(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    initial_money: int = Field(default=100, ge=0)
    initial_inventory: InventorySeed = Field(default_factory=InventorySeed)


class MarketSeed(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    map_x: float | None = Field(default=None, ge=0, le=100)
    map_y: float | None = Field(default=None, ge=0, le=100)


class RateSeed(BaseModel):
    market_code: str = Field(min_length=1, max_length=2)
    period: int = Field(ge=1, le=4)
    resource_type: Literal["dragon_egg", "time_device", "unicorn_blood", "basilisk_fang"]
    buy_price: int = Field(ge=0)
    sell_price: int = Field(ge=0)
    is_public: bool = True


def _default_teams() -> list[TeamSeed]:
    return [TeamSeed(name=f"第 {number} 隊") for number in range(1, 13)]


def _default_markets() -> list[MarketSeed]:
    return [MarketSeed(name=f"市場 {code}") for code in MARKET_CODES]


class SessionBootstrapRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    scheduled_start: datetime | None = None
    teams: list[TeamSeed] = Field(default_factory=_default_teams)
    markets: list[MarketSeed] = Field(default_factory=_default_markets)
    rates: list[RateSeed] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_layout(self):
        if len(self.teams) != 12:
            raise ValueError("場次必須設定 12 個小隊。")
        if len(self.markets) != 8:
            raise ValueError("場次必須設定 8 個市場。")
        if len({team.name for team in self.teams}) != len(self.teams):
            raise ValueError("小隊名稱不可重複。")
        if len({market.name for market in self.markets}) != len(self.markets):
            raise ValueError("市場名稱不可重複。")
        invalid_codes = {rate.market_code.upper() for rate in self.rates} - set(MARKET_CODES)
        if invalid_codes:
            raise ValueError(f"行情包含不存在的市場代碼：{', '.join(sorted(invalid_codes))}")
        return self


class AccessCodeView(BaseModel):
    label: str
    role: str
    code: str
    team_id: UUID | None = None
    market_id: UUID | None = None


class SessionBootstrapResponse(BaseModel):
    session_id: UUID
    status: str
    coordinator: AccessCodeView
    market_codes: list[AccessCodeView]
    team_codes: list[AccessCodeView]


def _new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


def _assert_setup_key(configured_key: str | None, provided_key: str | None) -> None:
    if not configured_key or not provided_key or not secrets.compare_digest(configured_key, provided_key):
        raise HTTPException(status_code=403, detail={"code": "SETUP_KEY_INVALID", "message": "初始化金鑰錯誤，無法建立場次。"})


@router.post("/sessions", response_model=SessionBootstrapResponse, status_code=201)
async def bootstrap_session(
    payload: SessionBootstrapRequest,
    x_setup_key: str | None = Header(default=None),
    pool: Pool = Depends(get_pool),
    settings: Settings = Depends(get_settings),
) -> SessionBootstrapResponse:
    _assert_setup_key(settings.setup_key, x_setup_key)
    status = "scheduled" if payload.scheduled_start else "draft"
    coordinator_code = _new_code()
    market_codes: list[AccessCodeView] = []
    team_codes: list[AccessCodeView] = []

    async with pool.acquire() as connection:
        async with connection.transaction():
            session_id = await connection.fetchval(
                "INSERT INTO game_sessions (name, status, scheduled_start) VALUES ($1, $2, $3) RETURNING id",
                payload.name,
                status,
                payload.scheduled_start,
            )
            await connection.execute("INSERT INTO game_event_counters (session_id) VALUES ($1)", session_id)
            coordinator_id = await connection.fetchval(
                """
                INSERT INTO access_codes (session_id, role, display_name, code_hash)
                VALUES ($1, 'coordinator', '總召控制台', $2) RETURNING id
                """,
                session_id,
                hash_access_code(coordinator_code),
            )
            if coordinator_id is None:
                raise HTTPException(status_code=500, detail={"code": "BOOTSTRAP_FAILED", "message": "無法建立總召代碼。"})

            team_ids: list[UUID] = []
            for number, team in enumerate(payload.teams, start=1):
                team_id = await connection.fetchval(
                    "INSERT INTO teams (session_id, number, name) VALUES ($1, $2, $3) RETURNING id",
                    session_id,
                    number,
                    team.name,
                )
                team_ids.append(team_id)
                await connection.execute("INSERT INTO team_wallets (team_id, balance) VALUES ($1, $2)", team_id, team.initial_money)
                for resource_type, quantity in team.initial_inventory.as_dict().items():
                    await connection.execute(
                        "INSERT INTO team_inventory (team_id, resource_type, quantity) VALUES ($1, $2, $3)",
                        team_id,
                        resource_type,
                        quantity,
                    )
                access_code = _new_code()
                await connection.execute(
                    """
                    INSERT INTO access_codes (session_id, role, display_name, team_id, code_hash)
                    VALUES ($1, 'team_facilitator', $2, $3, $4)
                    """,
                    session_id,
                    f"第 {number} 隊・{team.name}",
                    team_id,
                    hash_access_code(access_code),
                )
                team_codes.append(AccessCodeView(label=team.name, role="team_facilitator", code=access_code, team_id=team_id))

            market_ids: dict[str, UUID] = {}
            for code, market in zip(MARKET_CODES, payload.markets, strict=True):
                market_id = await connection.fetchval(
                    "INSERT INTO markets (session_id, code, name, map_x, map_y) VALUES ($1, $2, $3, $4, $5) RETURNING id",
                    session_id,
                    code,
                    market.name,
                    market.map_x,
                    market.map_y,
                )
                market_ids[code] = market_id
                access_code = _new_code()
                await connection.execute(
                    """
                    INSERT INTO access_codes (session_id, role, display_name, market_id, code_hash)
                    VALUES ($1, 'market_master', $2, $3, $4)
                    """,
                    session_id,
                    f"{code} 市場・{market.name}",
                    market_id,
                    hash_access_code(access_code),
                )
                market_codes.append(AccessCodeView(label=market.name, role="market_master", code=access_code, market_id=market_id))

            for rate in payload.rates:
                await connection.execute(
                    """
                    INSERT INTO market_rates (market_id, period, resource_type, buy_price, sell_price, is_public)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    market_ids[rate.market_code.upper()],
                    rate.period,
                    rate.resource_type,
                    rate.buy_price,
                    rate.sell_price,
                    rate.is_public,
                )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, action, payload) VALUES ($1, 'session.bootstrap', $2::jsonb)",
                session_id,
                json.dumps({"teams": len(team_ids), "markets": len(market_ids), "rates": len(payload.rates)}),
            )

    return SessionBootstrapResponse(
        session_id=session_id,
        status=status,
        coordinator=AccessCodeView(label="總召控制台", role="coordinator", code=coordinator_code),
        market_codes=market_codes,
        team_codes=team_codes,
    )


class RateBatchRequest(BaseModel):
    rates: list[RateSeed] = Field(min_length=1)


@router.put("/sessions/{session_id}/rates")
async def upsert_rates(
    session_id: UUID,
    payload: RateBatchRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, object]:
    require_session(context, session_id)
    async with pool.acquire() as connection:
        async with connection.transaction():
            markets = await connection.fetch("SELECT id, code FROM markets WHERE session_id = $1", session_id)
            market_ids = {market["code"]: market["id"] for market in markets}
            missing = sorted({rate.market_code.upper() for rate in payload.rates} - market_ids.keys())
            if missing:
                raise HTTPException(status_code=422, detail={"code": "MARKET_NOT_FOUND", "message": f"找不到市場：{', '.join(missing)}"})
            for rate in payload.rates:
                await connection.execute(
                    """
                    INSERT INTO market_rates (market_id, period, resource_type, buy_price, sell_price, is_public)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (market_id, period, resource_type)
                    DO UPDATE SET buy_price = EXCLUDED.buy_price, sell_price = EXCLUDED.sell_price, is_public = EXCLUDED.is_public
                    """,
                    market_ids[rate.market_code.upper()],
                    rate.period,
                    rate.resource_type,
                    rate.buy_price,
                    rate.sell_price,
                    rate.is_public,
                )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, payload) VALUES ($1, $2, 'rates.upsert', $3::jsonb)",
                session_id,
                context.access_id,
                json.dumps({"count": len(payload.rates)}),
            )
    return {"updated": len(payload.rates)}

