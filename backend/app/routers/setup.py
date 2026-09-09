import json
import secrets
from copy import deepcopy
from datetime import datetime
from uuid import UUID

from asyncpg import Pool
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..config import Settings, get_settings
from ..db import get_pool
from ..dependencies import require_roles, require_session
from ..game_clock import current_period as live_period
from ..game_seed import ensure_fixed_game_data
from ..game_config import (
    DEFAULT_BLACK_MARKET_CARDS,
    DEFAULT_INITIAL_INVENTORY,
    DEFAULT_PRODUCTS,
    DEFAULT_RULES,
    DEFAULT_TEAM_PROFILES,
    INITIAL_MONEY,
    MAP_IMAGE_MAX_LENGTH,
    MAP_IMAGE_PREFIXES,
    MARKET_CODES,
    TEAM_COUNT,
    TEAM_TONES,
    default_rates,
    normalize_config,
)
from ..security import AuthContext

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

class InventorySeed(BaseModel):
    model_config = ConfigDict(extra="allow")

    dragon_egg: int = Field(default=0, ge=0, le=0)
    time_device: int = Field(default=0, ge=0, le=0)
    unicorn_blood: int = Field(default=0, ge=0, le=0)
    basilisk_fang: int = Field(default=0, ge=0, le=0)

    def as_dict(self) -> dict[str, int]:
        return self.model_dump()


class TeamSeed(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    english_name: str = Field(default="", max_length=40)
    icon: str = Field(default="✦", min_length=1, max_length=4)
    description: str = Field(default="", max_length=120)
    tone: str = Field(default="aurora", pattern=rf"^({'|'.join(TEAM_TONES)})$")
    initial_money: int = Field(default=INITIAL_MONEY, ge=INITIAL_MONEY, le=INITIAL_MONEY)
    initial_inventory: InventorySeed = Field(default_factory=InventorySeed)


class MarketSeed(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    map_x: float | None = Field(default=None, ge=0, le=100)
    map_y: float | None = Field(default=None, ge=0, le=100)


class RateSeed(BaseModel):
    market_code: str = Field(min_length=1, max_length=2)
    period: int = Field(ge=1, le=4)
    resource_type: str = Field(min_length=2, max_length=40, pattern=r"^[a-z][a-z0-9_]{1,39}$")
    buy_price: int = Field(ge=0)
    sell_price: int = Field(ge=0)
    is_public: bool = True


class RulesConfig(BaseModel):
    period_count: int = Field(default=4, ge=4, le=4)
    period_duration_minutes: int = Field(default=15, ge=15, le=15)
    trade_quantity: int = Field(default=1, ge=1, le=1)
    same_market_trade_block: bool = True
    challenge_start_period: int = Field(default=3, ge=3, le=3)
    challenge_default_difficulty: int = Field(default=3, ge=3, le=3)
    challenge_occupied_difficulty: int = Field(default=4, ge=4, le=4)
    challenge_cooldown_minutes: int = Field(default=3, ge=3, le=3)
    ownership_rate_per_minute: int = Field(default=3, ge=3, le=3)
    magic_start_period: int = Field(default=1, ge=1, le=1)
    magic_reward_by_difficulty: list[int] = Field(default_factory=lambda: [1, 3, 5, 10, 20], min_length=5, max_length=5)
    black_market_start_period: int = Field(default=2, ge=2, le=2)
    black_market_draw_cost: int = Field(default=10, ge=10, le=10)
    guard_money_pouch: bool = True
    guard_minimum_team_present: bool = True


class MapConfig(BaseModel):
    image_data_url: str | None = Field(default=None, max_length=MAP_IMAGE_MAX_LENGTH)
    width: int | None = Field(default=None, ge=1, le=10_000)
    height: int | None = Field(default=None, ge=1, le=10_000)

    @model_validator(mode="after")
    def validate_image(self):
        if self.image_data_url is None:
            if self.width is not None or self.height is not None:
                raise ValueError("移除地圖時，圖片尺寸也必須清除。")
            return self
        if not self.image_data_url.startswith(MAP_IMAGE_PREFIXES):
            raise ValueError("地圖只能使用 PNG、JPEG 或 WebP 圖片。")
        if self.width is None or self.height is None:
            raise ValueError("地圖圖片必須同時提供原始寬高。")
        return self


class GameConfigPayload(BaseModel):
    products: list[dict[str, str]] = Field(default_factory=lambda: deepcopy(DEFAULT_PRODUCTS), min_length=4, max_length=4)
    rules: RulesConfig = Field(default_factory=lambda: RulesConfig(**DEFAULT_RULES))
    map: MapConfig = Field(default_factory=MapConfig)

    @model_validator(mode="after")
    def validate_config(self):
        if self.products != DEFAULT_PRODUCTS:
            raise ValueError("物資名稱與交易識別碼依遊戲規則固定，不能修改。")
        if self.rules.model_dump() != DEFAULT_RULES:
            raise ValueError("時段、獎勵與互動規則依遊戲規則固定，不能修改。")
        return self


def _default_teams() -> list[TeamSeed]:
    return [TeamSeed(**profile) for profile in DEFAULT_TEAM_PROFILES]


def _default_markets() -> list[MarketSeed]:
    return [MarketSeed(name=code) for code in MARKET_CODES]


class SessionBootstrapRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    coordinator_email: str = Field(min_length=5, max_length=320)
    scheduled_start: datetime | None = None
    teams: list[TeamSeed] = Field(default_factory=_default_teams)
    markets: list[MarketSeed] = Field(default_factory=_default_markets)
    config: GameConfigPayload = Field(default_factory=GameConfigPayload)

    @model_validator(mode="after")
    def validate_layout(self):
        if "@" not in self.coordinator_email:
            raise ValueError("總召 email 格式不正確。")
        if len(self.teams) != TEAM_COUNT:
            raise ValueError(f"場次必須設定 {TEAM_COUNT} 個小隊。")
        if len(self.markets) != 8:
            raise ValueError("場次必須設定 8 個市場。")
        if len({team.name for team in self.teams}) != len(self.teams):
            raise ValueError("小隊名稱不可重複。")
        if len({market.name for market in self.markets}) != len(self.markets):
            raise ValueError("市場名稱不可重複。")
        return self


class SessionBootstrapResponse(BaseModel):
    session_id: UUID
    status: str


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

    async with pool.acquire() as connection:
        async with connection.transaction():
            fixed_config = normalize_config(payload.config.model_dump())
            session_id = await connection.fetchval(
                "INSERT INTO game_sessions (name, status, scheduled_start, config) VALUES ($1, $2, $3, $4::jsonb) RETURNING id",
                payload.name,
                status,
                payload.scheduled_start,
                json.dumps(fixed_config),
            )
            await connection.execute("INSERT INTO game_event_counters (session_id) VALUES ($1)", session_id)
            village_duration = DEFAULT_RULES["period_count"] * DEFAULT_RULES["period_duration_minutes"]
            default_stages = (("活米村", "magic_village", 1, 0, village_duration, {"period_count": DEFAULT_RULES["period_count"]}),)
            stage_ids: list[UUID] = []
            for name, stage_type, sort_order, start_offset_ms, duration_minutes, config in default_stages:
                stage_ids.append(await connection.fetchval(
                    """
                    INSERT INTO activity_stages (
                      session_id, name, stage_type, sort_order, start_offset_ms,
                      duration_minutes, config
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                    RETURNING id
                    """,
                    session_id,
                    name,
                    stage_type,
                    sort_order,
                    start_offset_ms,
                    duration_minutes,
                    json.dumps(config),
                ))
            coordinator_id = await connection.fetchval(
                """
                INSERT INTO participants (session_id, participant_no, display_name, email)
                VALUES ($1, 'COORDINATOR', '總召', $2)
                RETURNING id
                """,
                session_id,
                payload.coordinator_email.strip().lower(),
            )
            if coordinator_id is None:
                raise HTTPException(status_code=500, detail={"code": "BOOTSTRAP_FAILED", "message": "無法建立總召身分。"})
            for stage_id in stage_ids:
                await connection.execute(
                    """
                    INSERT INTO stage_role_assignments (session_id, stage_id, participant_id, role, scope_type)
                    VALUES ($1, $2, $3, 'coordinator', 'session')
                    """,
                    session_id,
                    stage_id,
                    coordinator_id,
                )

            team_ids: list[UUID] = []
            for number, team in enumerate(payload.teams, start=1):
                team_id = await connection.fetchval(
                    """
                    INSERT INTO teams (session_id, number, name, english_name, icon, description, tone)
                    VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id
                    """,
                    session_id,
                    number,
                    team.name,
                    team.english_name,
                    team.icon,
                    team.description,
                    team.tone,
                )
                team_ids.append(team_id)
                await connection.execute("INSERT INTO team_wallets (team_id, balance) VALUES ($1, $2)", team_id, INITIAL_MONEY)
                for product in DEFAULT_PRODUCTS:
                    await connection.execute(
                        "INSERT INTO team_inventory (team_id, resource_type, quantity) VALUES ($1, $2, $3)",
                        team_id,
                        product["key"],
                        DEFAULT_INITIAL_INVENTORY[product["key"]],
                    )

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

            for rate in default_rates():
                await connection.execute(
                    """
                    INSERT INTO market_rates (market_id, period, resource_type, buy_price, sell_price, is_public)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    market_ids[rate["market_code"]],
                    rate["period"],
                    rate["resource_type"],
                    rate["buy_price"],
                    rate["sell_price"],
                    rate["is_public"],
                )
            for card in DEFAULT_BLACK_MARKET_CARDS:
                await connection.execute(
                    """
                    INSERT INTO black_market_cards (session_id, name, description, effect_type, effect_config, enabled)
                    VALUES ($1, $2, $3, $4, $5::jsonb, TRUE)
                    """,
                    session_id,
                    card["name"],
                    card["description"],
                    card["effect_type"],
                    json.dumps(card["effect_config"]),
                )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, action, payload) VALUES ($1, 'session.bootstrap', $2::jsonb)",
                session_id,
                json.dumps({"teams": len(team_ids), "markets": len(market_ids), "rates": len(default_rates()), "black_market_cards": len(DEFAULT_BLACK_MARKET_CARDS)}),
            )

    return SessionBootstrapResponse(
        session_id=session_id,
        status=status,
    )


class RateBatchRequest(BaseModel):
    rates: list[RateSeed] = Field(min_length=1)


class TeamConfigUpdate(BaseModel):
    number: int = Field(ge=1, le=TEAM_COUNT)
    name: str = Field(min_length=1, max_length=40)
    english_name: str = Field(default="", max_length=40)
    icon: str = Field(default="✦", min_length=1, max_length=4)
    description: str = Field(default="", max_length=120)
    tone: str = Field(default="aurora", pattern=rf"^({'|'.join(TEAM_TONES)})$")
    initial_money: int = Field(default=INITIAL_MONEY, ge=INITIAL_MONEY, le=INITIAL_MONEY)
    initial_inventory: InventorySeed = Field(default_factory=InventorySeed)


class MarketConfigUpdate(BaseModel):
    code: str = Field(min_length=1, max_length=1)
    name: str = Field(min_length=1, max_length=40)
    map_x: float | None = Field(default=None, ge=0, le=100)
    map_y: float | None = Field(default=None, ge=0, le=100)


async def _assert_editable_session(connection, session_id: UUID) -> None:
    status = await connection.fetchval("SELECT status FROM game_sessions WHERE id = $1 FOR UPDATE", session_id)
    if status is None:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "找不到這個遊戲場次。"})
    if status not in {"draft", "scheduled"}:
        raise HTTPException(status_code=409, detail={"code": "SESSION_LOCKED", "message": "場次開始後不能直接修改開局設定。"})


@router.get("/sessions/{session_id}")
async def get_setup(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, object]:
    require_session(context, session_id)
    async with pool.acquire() as connection:
        async with connection.transaction():
            session = await connection.fetchrow(
                "SELECT id, name, status, scheduled_start, current_period, manual_period_override, config, started_at, paused_at, accumulated_pause_ms FROM game_sessions WHERE id = $1 FOR UPDATE",
                session_id,
            )
            if session is not None and session["status"] in {"draft", "scheduled"}:
                await ensure_fixed_game_data(connection, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "找不到這個遊戲場次。"})
    teams = await pool.fetch(
        """
        SELECT t.id, t.number, t.name, t.english_name, t.icon, t.description, t.tone, w.balance AS initial_money,
               COALESCE(jsonb_object_agg(i.resource_type, i.quantity) FILTER (WHERE i.resource_type IS NOT NULL), '{}'::jsonb) AS initial_inventory
        FROM teams t
        JOIN team_wallets w ON w.team_id = t.id
        LEFT JOIN team_inventory i ON i.team_id = t.id
        WHERE t.session_id = $1
        GROUP BY t.id, w.balance
        ORDER BY t.number
        """,
        session_id,
    )
    markets = await pool.fetch(
        "SELECT id, code, name, map_x, map_y FROM markets WHERE session_id = $1 ORDER BY code",
        session_id,
    )
    rates = await pool.fetch(
        """
        SELECT m.code AS market_code, r.period, r.resource_type, r.buy_price, r.sell_price, r.is_public
        FROM market_rates r JOIN markets m ON m.id = r.market_id
        WHERE m.session_id = $1 ORDER BY m.code, r.period, r.resource_type
        """,
        session_id,
    )
    session_summary = {key: value for key, value in dict(session).items() if key not in {"config", "started_at", "paused_at", "accumulated_pause_ms"}}
    session_summary["current_period"] = live_period(session, DEFAULT_RULES)
    return {
        "session": session_summary,
        "config": normalize_config(session["config"]),
        "teams": [dict(team) for team in teams],
        "markets": [dict(market) for market in markets],
        "rates": [dict(rate) for rate in rates],
    }


@router.put("/sessions/{session_id}/config")
async def update_config(
    session_id: UUID,
    payload: GameConfigPayload,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, bool]:
    require_session(context, session_id)
    async with pool.acquire() as connection:
        async with connection.transaction():
            await _assert_editable_session(connection, session_id)
            await connection.execute(
                "UPDATE game_sessions SET config = $1::jsonb, updated_at = NOW() WHERE id = $2",
                json.dumps(normalize_config(payload.model_dump())),
                session_id,
            )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, payload) VALUES ($1, $2, 'setup.config.update', $3::jsonb)",
                session_id,
                context.access_id,
                json.dumps({"map_updated": True}),
            )
    return {"updated": True}


@router.put("/sessions/{session_id}/teams")
async def update_teams(
    session_id: UUID,
    teams: list[TeamConfigUpdate],
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, int]:
    require_session(context, session_id)
    if len(teams) != TEAM_COUNT or len({team.number for team in teams}) != TEAM_COUNT:
        raise HTTPException(status_code=422, detail={"code": "TEAM_LAYOUT_INVALID", "message": f"必須提供 1–{TEAM_COUNT} 號全部小隊。"})
    async with pool.acquire() as connection:
        async with connection.transaction():
            await _assert_editable_session(connection, session_id)
            for team in teams:
                team_id = await connection.fetchval("SELECT id FROM teams WHERE session_id = $1 AND number = $2", session_id, team.number)
                if team_id is None:
                    raise HTTPException(status_code=422, detail={"code": "TEAM_NOT_FOUND", "message": f"找不到第 {team.number} 隊。"})
                await connection.execute(
                    "UPDATE teams SET name = $1, english_name = $2, icon = $3, description = $4, tone = $5 WHERE id = $6",
                    team.name,
                    team.english_name,
                    team.icon,
                    team.description,
                    team.tone,
                    team_id,
                )
                await connection.execute(
                    "UPDATE access_codes SET display_name = $1 WHERE team_id = $2 AND role = 'team_facilitator' AND active = TRUE",
                    f"第 {team.number} 隊・{team.name}",
                    team_id,
                )
                await connection.execute("UPDATE team_wallets SET balance = $1, updated_at = NOW() WHERE team_id = $2", INITIAL_MONEY, team_id)
                for resource_type, quantity in DEFAULT_INITIAL_INVENTORY.items():
                    await connection.execute(
                        "UPDATE team_inventory SET quantity = $1, updated_at = NOW() WHERE team_id = $2 AND resource_type = $3",
                        quantity,
                        team_id,
                        resource_type,
                    )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, payload) VALUES ($1, $2, 'setup.teams.update', $3::jsonb)",
                session_id,
                context.access_id,
                json.dumps({"count": len(teams)}),
            )
    return {"updated": len(teams)}


@router.put("/sessions/{session_id}/markets")
async def update_markets(
    session_id: UUID,
    markets: list[MarketConfigUpdate],
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, int]:
    require_session(context, session_id)
    if len(markets) != 8 or {market.code for market in markets} != set(MARKET_CODES):
        raise HTTPException(status_code=422, detail={"code": "MARKET_LAYOUT_INVALID", "message": "必須提供 A–H 全部市場。"})
    async with pool.acquire() as connection:
        async with connection.transaction():
            await _assert_editable_session(connection, session_id)
            for market in markets:
                await connection.execute(
                    "UPDATE markets SET name = $1, map_x = $2, map_y = $3 WHERE session_id = $4 AND code = $5",
                    market.name,
                    market.map_x,
                    market.map_y,
                    session_id,
                    market.code,
                )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, payload) VALUES ($1, $2, 'setup.markets.update', $3::jsonb)",
                session_id,
                context.access_id,
                json.dumps({"count": len(markets)}),
            )
    return {"updated": len(markets)}


@router.put("/sessions/{session_id}/rates")
async def upsert_rates(
    session_id: UUID,
    payload: RateBatchRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, object]:
    require_session(context, session_id)
    raise HTTPException(
        status_code=409,
        detail={"code": "MARKET_RATES_FIXED", "message": "市場行情依遊戲規則固定，不能在系統內修改。"},
    )
