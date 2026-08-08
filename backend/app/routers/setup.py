import json
import secrets
from datetime import datetime
from uuid import UUID, uuid4

from asyncpg import Pool
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..config import Settings, get_settings
from ..db import get_pool
from ..dependencies import require_roles, require_session
from ..game_config import DEFAULT_PRODUCTS, DEFAULT_RULES, DEFAULT_TEAM_PROFILES, MAP_IMAGE_MAX_LENGTH, MAP_IMAGE_PREFIXES, TEAM_COUNT, TEAM_TONES, normalize_config
from ..security import AuthContext, hash_access_code

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

MARKET_CODES = tuple("ABCDEFGH")
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class InventorySeed(BaseModel):
    model_config = ConfigDict(extra="allow")

    dragon_egg: int = Field(default=0, ge=0)
    time_device: int = Field(default=0, ge=0)
    unicorn_blood: int = Field(default=0, ge=0)
    basilisk_fang: int = Field(default=0, ge=0)

    def as_dict(self) -> dict[str, int]:
        return self.model_dump()


class TeamSeed(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    english_name: str = Field(default="", max_length=40)
    icon: str = Field(default="✦", min_length=1, max_length=4)
    description: str = Field(default="", max_length=120)
    tone: str = Field(default="aurora", pattern=rf"^({'|'.join(TEAM_TONES)})$")
    initial_money: int = Field(default=100, ge=0)
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


class ProductConfig(BaseModel):
    key: str = Field(min_length=2, max_length=40, pattern=r"^[a-z][a-z0-9_]{1,39}$")
    name: str = Field(min_length=1, max_length=40)
    short_name: str = Field(min_length=1, max_length=6)
    unit_name: str = Field(min_length=1, max_length=8)


class RulesConfig(BaseModel):
    period_count: int = Field(default=4, ge=1, le=4)
    period_duration_minutes: int = Field(default=15, ge=1, le=120)
    trade_quantity: int = Field(default=1, ge=1, le=10)
    same_market_trade_block: bool = True
    challenge_start_period: int = Field(default=3, ge=1, le=4)
    challenge_default_difficulty: int = Field(default=3, ge=1, le=5)
    challenge_occupied_difficulty: int = Field(default=4, ge=1, le=5)
    challenge_cooldown_minutes: int = Field(default=3, ge=0, le=120)
    ownership_rate_per_minute: int = Field(default=3, ge=0, le=1000)
    magic_start_period: int = Field(default=1, ge=1, le=4)
    magic_reward_by_difficulty: list[int] = Field(default_factory=lambda: [1, 3, 5, 10, 20], min_length=5, max_length=5)
    black_market_start_period: int = Field(default=2, ge=1, le=4)
    black_market_draw_cost: int = Field(default=10, ge=0, le=100000)
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
    products: list[ProductConfig] = Field(default_factory=lambda: [ProductConfig(**item) for item in DEFAULT_PRODUCTS], min_length=4, max_length=4)
    rules: RulesConfig = Field(default_factory=lambda: RulesConfig(**DEFAULT_RULES))
    map: MapConfig = Field(default_factory=MapConfig)

    @model_validator(mode="after")
    def validate_config(self):
        if len({product.key for product in self.products}) != len(self.products):
            raise ValueError("商品交易識別碼不可重複。")
        if len({product.name for product in self.products}) != len(self.products):
            raise ValueError("商品名稱不可重複，避免現場辨識錯誤。")
        if self.rules.challenge_start_period > self.rules.period_count:
            raise ValueError("據點挑戰開放時段不可晚於總時段數。")
        if self.rules.magic_start_period > self.rules.period_count:
            raise ValueError("隱藏魔王開放時段不可晚於總時段數。")
        if self.rules.black_market_start_period > self.rules.period_count:
            raise ValueError("黑心商人開放時段不可晚於總時段數。")
        if any(reward < 0 for reward in self.rules.magic_reward_by_difficulty):
            raise ValueError("魔王獎勵不可為負數。")
        return self


def _default_teams() -> list[TeamSeed]:
    return [TeamSeed(**profile) for profile in DEFAULT_TEAM_PROFILES]


def _default_markets() -> list[MarketSeed]:
    return [MarketSeed(name=code) for code in MARKET_CODES]


class SessionBootstrapRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    scheduled_start: datetime | None = None
    teams: list[TeamSeed] = Field(default_factory=_default_teams)
    markets: list[MarketSeed] = Field(default_factory=_default_markets)
    rates: list[RateSeed] = Field(default_factory=list)
    config: GameConfigPayload = Field(default_factory=GameConfigPayload)

    @model_validator(mode="after")
    def validate_layout(self):
        if len(self.teams) != TEAM_COUNT:
            raise ValueError(f"場次必須設定 {TEAM_COUNT} 個小隊。")
        if len(self.markets) != 8:
            raise ValueError("場次必須設定 8 個市場。")
        if len({team.name for team in self.teams}) != len(self.teams):
            raise ValueError("小隊名稱不可重複。")
        if len({market.name for market in self.markets}) != len(self.markets):
            raise ValueError("市場名稱不可重複。")
        invalid_codes = {rate.market_code.upper() for rate in self.rates} - set(MARKET_CODES)
        if invalid_codes:
            raise ValueError(f"行情包含不存在的市場代碼：{', '.join(sorted(invalid_codes))}")
        invalid_products = {rate.resource_type for rate in self.rates} - {product.key for product in self.config.products}
        if invalid_products:
            raise ValueError(f"行情包含不存在的商品識別碼：{', '.join(sorted(invalid_products))}")
        return self


class AccessCodeView(BaseModel):
    label: str
    role: str
    code: str
    team_id: UUID | None = None
    market_id: UUID | None = None


class AccessCodeSummary(BaseModel):
    access_id: UUID
    role: str
    display_name: str
    team_id: UUID | None = None
    market_id: UUID | None = None
    active: bool


class AccessCodePasswordUpdate(BaseModel):
    access_id: UUID
    password: str = Field(min_length=4, max_length=64)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("登入密碼不可只有空白。")
        return value


class AccessCodePasswordBatchRequest(BaseModel):
    passwords: list[AccessCodePasswordUpdate] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def validate_unique_access_ids(self):
        access_ids = [item.access_id for item in self.passwords]
        if len(set(access_ids)) != len(access_ids):
            raise ValueError("同一個身分不可重複設定密碼。")
        return self


class SessionBootstrapResponse(BaseModel):
    session_id: UUID
    status: str
    coordinator: AccessCodeView
    magic_boss: AccessCodeView
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
    magic_boss_code = _new_code()
    market_codes: list[AccessCodeView] = []
    team_codes: list[AccessCodeView] = []

    async with pool.acquire() as connection:
        async with connection.transaction():
            session_id = await connection.fetchval(
                "INSERT INTO game_sessions (name, status, scheduled_start, config) VALUES ($1, $2, $3, $4::jsonb) RETURNING id",
                payload.name,
                status,
                payload.scheduled_start,
                json.dumps(payload.config.model_dump()),
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

            await connection.execute(
                """
                INSERT INTO access_codes (session_id, role, display_name, code_hash)
                VALUES ($1, 'magic_boss', '隱藏魔王工作台', $2)
                """,
                session_id,
                hash_access_code(magic_boss_code),
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
                await connection.execute("INSERT INTO team_wallets (team_id, balance) VALUES ($1, $2)", team_id, team.initial_money)
                inventory_seed = team.initial_inventory.as_dict()
                for index, product in enumerate(payload.config.products):
                    legacy_key = DEFAULT_PRODUCTS[index]["key"]
                    quantity = inventory_seed.get(product.key, inventory_seed.get(legacy_key, 0))
                    await connection.execute(
                        "INSERT INTO team_inventory (team_id, resource_type, quantity) VALUES ($1, $2, $3)",
                        team_id,
                        product.key,
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
        magic_boss=AccessCodeView(label="隱藏魔王工作台", role="magic_boss", code=magic_boss_code),
        market_codes=market_codes,
        team_codes=team_codes,
    )


@router.post("/sessions/{session_id}/magic-boss-code", response_model=AccessCodeView)
async def rotate_magic_boss_code(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> AccessCodeView:
    require_session(context, session_id)
    access_code = _new_code()
    async with pool.acquire() as connection:
        async with connection.transaction():
            session_exists = await connection.fetchval("SELECT EXISTS(SELECT 1 FROM game_sessions WHERE id = $1)", session_id)
            if not session_exists:
                raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "找不到這個遊戲場次。"})
            await connection.execute("UPDATE access_codes SET active = FALSE WHERE session_id = $1 AND role = 'magic_boss'", session_id)
            await connection.execute(
                "INSERT INTO access_codes (session_id, role, display_name, code_hash) VALUES ($1, 'magic_boss', '隱藏魔王工作台', $2)",
                session_id,
                hash_access_code(access_code),
            )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, payload) VALUES ($1, $2, 'magic_boss_code.rotate', $3::jsonb)",
                session_id,
                context.access_id,
                json.dumps({"role": "magic_boss"}),
            )
    return AccessCodeView(label="隱藏魔王工作台", role="magic_boss", code=access_code)


@router.get("/sessions/{session_id}/access-codes", response_model=list[AccessCodeSummary])
async def list_access_codes(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> list[AccessCodeSummary]:
    require_session(context, session_id)
    rows = await pool.fetch(
        """
        SELECT id AS access_id, role, display_name, team_id, market_id, active
        FROM access_codes
        WHERE session_id = $1 AND role <> 'coordinator' AND active = TRUE
        ORDER BY CASE role
            WHEN 'magic_boss' THEN 1
            WHEN 'market_master' THEN 2
            WHEN 'team_facilitator' THEN 3
            ELSE 4
        END, display_name
        """,
        session_id,
    )
    return [AccessCodeSummary(**dict(row)) for row in rows]


@router.put("/sessions/{session_id}/access-code-passwords")
async def update_access_code_passwords(
    session_id: UUID,
    payload: AccessCodePasswordBatchRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, int]:
    require_session(context, session_id)
    submitted_ids = [item.access_id for item in payload.passwords]
    async with pool.acquire() as connection:
        async with connection.transaction():
            rows = await connection.fetch(
                """
                SELECT id, role
                FROM access_codes
                WHERE session_id = $1 AND active = TRUE AND id = ANY($2::uuid[])
                FOR UPDATE
                """,
                session_id,
                submitted_ids,
            )
            access_codes = {row["id"]: row for row in rows}
            missing_ids = [access_id for access_id in submitted_ids if access_id not in access_codes]
            if missing_ids:
                raise HTTPException(status_code=422, detail={"code": "ACCESS_CODE_NOT_FOUND", "message": "找不到可設定的角色登入身分。"})
            if any(row["role"] == "coordinator" for row in access_codes.values()):
                raise HTTPException(status_code=422, detail={"code": "COORDINATOR_PASSWORD_FIXED", "message": "總召密碼維持場次建立時的預設密碼。"})

            for item in payload.passwords:
                await connection.execute(
                    "UPDATE access_codes SET code_hash = $1 WHERE id = $2",
                    hash_access_code(item.password),
                    item.access_id,
                )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, payload) VALUES ($1, $2, 'access_code.password.update', $3::jsonb)",
                session_id,
                context.access_id,
                json.dumps({"count": len(payload.passwords), "roles": sorted({access_codes[item.access_id]["role"] for item in payload.passwords})}),
            )
    return {"updated": len(payload.passwords)}


class RateBatchRequest(BaseModel):
    rates: list[RateSeed] = Field(min_length=1)


class TeamConfigUpdate(BaseModel):
    number: int = Field(ge=1, le=TEAM_COUNT)
    name: str = Field(min_length=1, max_length=40)
    english_name: str = Field(default="", max_length=40)
    icon: str = Field(default="✦", min_length=1, max_length=4)
    description: str = Field(default="", max_length=120)
    tone: str = Field(default="aurora", pattern=rf"^({'|'.join(TEAM_TONES)})$")
    initial_money: int = Field(ge=0)
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


async def _rename_product_identifiers(connection, session_id: UUID, previous_config: object, next_config: GameConfigPayload) -> None:
    previous_products = normalize_config(previous_config)["products"]
    renames = [
        (old["key"], product.key, f"__product_rename_{uuid4().hex}")
        for old, product in zip(previous_products, next_config.products, strict=True)
        if old["key"] != product.key
    ]
    if not renames:
        return

    # Move every old value to a temporary namespace first so swapping identifiers
    # (for example A -> B and B -> A) cannot collide with unique indexes.
    for old_key, _, temporary_key in renames:
        await connection.execute(
            "UPDATE team_inventory SET resource_type = $1 WHERE resource_type = $2 AND team_id IN (SELECT id FROM teams WHERE session_id = $3)",
            temporary_key,
            old_key,
            session_id,
        )
        await connection.execute(
            "UPDATE market_rates SET resource_type = $1 WHERE resource_type = $2 AND market_id IN (SELECT id FROM markets WHERE session_id = $3)",
            temporary_key,
            old_key,
            session_id,
        )
        await connection.execute(
            "UPDATE transactions SET resource_type = $1 WHERE resource_type = $2 AND session_id = $3",
            temporary_key,
            old_key,
            session_id,
        )

    for _, new_key, temporary_key in renames:
        await connection.execute(
            "UPDATE team_inventory SET resource_type = $1 WHERE resource_type = $2 AND team_id IN (SELECT id FROM teams WHERE session_id = $3)",
            new_key,
            temporary_key,
            session_id,
        )
        await connection.execute(
            "UPDATE market_rates SET resource_type = $1 WHERE resource_type = $2 AND market_id IN (SELECT id FROM markets WHERE session_id = $3)",
            new_key,
            temporary_key,
            session_id,
        )
        await connection.execute(
            "UPDATE transactions SET resource_type = $1 WHERE resource_type = $2 AND session_id = $3",
            new_key,
            temporary_key,
            session_id,
        )


@router.get("/sessions/{session_id}")
async def get_setup(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("coordinator")),
) -> dict[str, object]:
    require_session(context, session_id)
    session = await pool.fetchrow(
        "SELECT id, name, status, scheduled_start, current_period, config FROM game_sessions WHERE id = $1",
        session_id,
    )
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
    return {
        "session": {key: value for key, value in dict(session).items() if key != "config"},
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
            previous_config = await connection.fetchval("SELECT config FROM game_sessions WHERE id = $1", session_id)
            await _rename_product_identifiers(connection, session_id, previous_config, payload)
            await connection.execute(
                "UPDATE game_sessions SET config = $1::jsonb, updated_at = NOW() WHERE id = $2",
                json.dumps(payload.model_dump()),
                session_id,
            )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, payload) VALUES ($1, $2, 'setup.config.update', $3::jsonb)",
                session_id,
                context.access_id,
                json.dumps({"products": len(payload.products), "rules": payload.rules.model_dump()}),
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
                await connection.execute("UPDATE team_wallets SET balance = $1, updated_at = NOW() WHERE team_id = $2", team.initial_money, team_id)
                for resource_type, quantity in team.initial_inventory.as_dict().items():
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
    async with pool.acquire() as connection:
        async with connection.transaction():
            await _assert_editable_session(connection, session_id)
            stored_config = normalize_config(await connection.fetchval("SELECT config FROM game_sessions WHERE id = $1", session_id))
            allowed_products = {product["key"] for product in stored_config["products"]}
            invalid_products = sorted({rate.resource_type for rate in payload.rates} - allowed_products)
            if invalid_products:
                raise HTTPException(status_code=422, detail={"code": "PRODUCT_NOT_CONFIGURED", "message": f"找不到商品識別碼：{', '.join(invalid_products)}"})
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
