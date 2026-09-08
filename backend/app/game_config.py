"""Canonical rules for the 2026 活米村 field game.

The rule sheet is the source of truth for gameplay. Only presentation data
(team profiles) and the map are session-specific; a coordinator must not be
able to accidentally alter money, timing, goods, or market prices mid-prep.
"""

from copy import deepcopy
from typing import Any


RESOURCE_TYPES = ("dragon_egg", "time_device", "unicorn_blood", "basilisk_fang")
MARKET_CODES = tuple("ABCDEFGH")
TEAM_COUNT = 12
TEAM_TONES = ("aurora", "ignis", "terra", "aqua", "nova", "solis", "ventus", "luna")
INITIAL_MONEY = 15
MAP_IMAGE_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/webp;base64,",
)
MAP_IMAGE_MAX_LENGTH = 9_000_000

DEFAULT_PRODUCTS: list[dict[str, Any]] = [
    {"key": "dragon_egg", "name": "龍蛋", "short_name": "A", "unit_name": "個"},
    {"key": "time_device", "name": "時光器", "short_name": "B", "unit_name": "個"},
    {"key": "unicorn_blood", "name": "獨角獸的血", "short_name": "C", "unit_name": "瓶"},
    {"key": "basilisk_fang", "name": "蛇妖牙齒", "short_name": "D", "unit_name": "根"},
]

DEFAULT_TEAM_PROFILES: list[dict[str, Any]] = [
    {
        "name": f"第 {number} 隊",
        "english_name": f"TEAM {number:02d}",
        "icon": str(number),
        "description": "等待總召設定隊名",
        "tone": TEAM_TONES[(number - 1) % len(TEAM_TONES)],
    }
    for number in range(1, TEAM_COUNT + 1)
]

DEFAULT_INITIAL_INVENTORY = {resource: 0 for resource in RESOURCE_TYPES}

DEFAULT_RULES: dict[str, Any] = {
    "period_count": 4,
    "period_duration_minutes": 15,
    "trade_quantity": 1,
    "same_market_trade_block": True,
    "challenge_start_period": 3,
    "challenge_default_difficulty": 3,
    "challenge_occupied_difficulty": 4,
    "challenge_cooldown_minutes": 3,
    "ownership_rate_per_minute": 3,
    "magic_start_period": 1,
    "magic_reward_by_difficulty": [1, 3, 5, 10, 20],
    "black_market_start_period": 2,
    "black_market_draw_cost": 10,
    "guard_money_pouch": True,
    "guard_minimum_team_present": True,
}

DEFAULT_MAP: dict[str, Any] = {"image_data_url": None, "width": None, "height": None}

# 收購 = a team sells to the market; 出售 = a team buys from the market.
# A zero price marks an unavailable direction, never a free trade.
_MARKET_PRICE_SHEET: dict[int, dict[str, dict[str, dict[str, int]]]] = {
    1: {
        "A": {"sell": {"A": 7, "C": 4}, "buy": {"A": 5}},
        "B": {"sell": {"C": 7, "D": 6}, "buy": {"B": 6}},
        "C": {"sell": {"B": 4, "D": 5}, "buy": {"C": 5}},
        "D": {"sell": {"B": 7, "C": 5}, "buy": {"D": 5}},
        "E": {"sell": {"B": 8, "D": 7}, "buy": {"A": 6}},
        "F": {"sell": {"A": 6, "B": 3}, "buy": {"B": 5}},
        "G": {"sell": {"A": 5, "C": 5}, "buy": {"C": 6}},
        "H": {"sell": {"A": 4, "D": 5}, "buy": {"D": 6}},
    },
    2: {
        "A": {"sell": {"B": 5, "D": 7}, "buy": {"A": 3}},
        "B": {"sell": {"A": 4, "D": 6}, "buy": {"B": 4}},
        "C": {"sell": {"A": 5, "B": 5, "D": 3}, "buy": {"C": 7}},
        "D": {"sell": {"C": 6}, "buy": {"D": 7}},
        "E": {"sell": {"B": 7}, "buy": {"A": 4}},
        "F": {"sell": {"C": 4, "D": 7}, "buy": {"B": 6}},
        "G": {"sell": {"C": 7}, "buy": {"C": 5}},
        "H": {"sell": {"A": 5, "B": 6}, "buy": {"D": 4}},
    },
    3: {
        "A": {"sell": {"A": 6, "B": 4}, "buy": {"A": 4}},
        "B": {"sell": {"C": 7}, "buy": {"B": 4}},
        "C": {"sell": {"D": 6}, "buy": {"C": 7}},
        "D": {"sell": {"A": 5, "B": 5}, "buy": {"D": 7}},
        "E": {"sell": {"B": 2, "C": 8}, "buy": {"A": 8}},
        "F": {"sell": {"C": 4, "D": 7}, "buy": {"B": 5}},
        "G": {"sell": {"A": 7, "C": 3, "D": 4}, "buy": {"C": 3}},
        "H": {"sell": {"B": 10, "D": 5}, "buy": {"D": 8}},
    },
    4: {
        "A": {"sell": {"C": 7, "D": 2}, "buy": {"A": 4}},
        "B": {"sell": {"B": 6, "D": 7}, "buy": {"B": 4}},
        "C": {"sell": {"A": 5, "B": 7}, "buy": {"C": 3}},
        "D": {"sell": {"C": 4}, "buy": {"D": 3}},
        "E": {"sell": {"A": 7, "D": 6}, "buy": {"A": 5}},
        "F": {"sell": {"B": 7, "D": 7}, "buy": {"B": 5}},
        "G": {"sell": {"A": 6, "C": 7}, "buy": {"C": 6}},
        "H": {"sell": {"B": 8}, "buy": {"D": 4}},
    },
}


def default_rates() -> list[dict[str, Any]]:
    """Return all 128 fixed market-direction rows in the API schema."""
    rates: list[dict[str, Any]] = []
    for period, markets in _MARKET_PRICE_SHEET.items():
        for market_code in MARKET_CODES:
            prices = markets[market_code]
            for product in DEFAULT_PRODUCTS:
                short_name = product["short_name"]
                rates.append(
                    {
                        "market_code": market_code,
                        "period": period,
                        "resource_type": product["key"],
                        "buy_price": prices["buy"].get(short_name, 0),
                        "sell_price": prices["sell"].get(short_name, 0),
                        "is_public": True,
                    }
                )
    return rates


DEFAULT_BLACK_MARKET_CARDS: list[dict[str, Any]] = [
    {"name": "古靈閣大劫案", "description": "偷取場上金幣最多的隊伍金幣；金額依現場總召裁定。", "effect_type": "manual_steal_leader", "effect_config": {}},
    {"name": "榮恩的斷魔杖", "description": "沒事發生。", "effect_type": "manual_no_effect", "effect_config": {}},
    {"name": "四次元口袋", "description": "下一筆交易可一次交易至多 5 個相同物資。", "effect_type": "next_trade_quantity_five", "effect_config": {"max_quantity": 5}},
    {"name": "MAGA", "description": "該組繳交 10% 稅。", "effect_type": "manual_tax_percent", "effect_config": {"percent": 10}},
    {"name": "代罪羔羊", "description": "效果依現場總召裁定。", "effect_type": "manual_unresolved", "effect_config": {}},
    {"name": "老熟人", "description": "下次購買可折扣 1 或 2 元，由現場裁定。", "effect_type": "manual_next_purchase_discount", "effect_config": {}},
    {"name": "黑道集團", "description": "店員成為你的小弟，向下一個人收過路費。", "effect_type": "manual_toll", "effect_config": {}},
    {"name": "出人頭地", "description": "佔領的據點收入增加至 4 枚／分鐘。", "effect_type": "manual_ownership_bonus", "effect_config": {"rate_per_minute": 4}},
    {"name": "晚安馬卡巴卡", "description": "該組佔領的據點全部歸還給關主。", "effect_type": "manual_return_all_ownership", "effect_config": {}},
    {"name": "幸福三百天", "description": "直接獲得學姊給的 30 元。", "effect_type": "grant_money", "effect_config": {"amount": 30}},
    {"name": "從從容容游刃有餘", "description": "接下來 3 分鐘不可以奔跑（走速大於 5 km/hr）。", "effect_type": "manual_no_running", "effect_config": {"minutes": 3, "max_kmh": 5}},
    {"name": "道路施工", "description": "將一條路封掉。", "effect_type": "manual_close_road", "effect_config": {}},
    {"name": "是這樣沒錯但不是這樣", "description": "接下來兩次交易隊輔只能說「不是喔／不是這樣喔」。", "effect_type": "manual_speech_restriction", "effect_config": {"trades": 2}},
    {"name": "天王星發電", "description": "獲得天王星出的物理考卷一張。", "effect_type": "manual_physics_exam", "effect_config": {}},
    {"name": "學姊我不想努力了", "description": "學姊開直升機去幫你交易一次。", "effect_type": "manual_helicopter_trade", "effect_config": {"trades": 1}},
    {"name": "神奇海螺", "description": "選擇一市場下階段物價。", "effect_type": "manual_choose_next_market_price", "effect_config": {}},
    {"name": "我是奶龍", "description": "竹女總召是奶龍。", "effect_type": "manual_no_effect", "effect_config": {}},
]


def default_config() -> dict[str, Any]:
    return {"products": deepcopy(DEFAULT_PRODUCTS), "rules": deepcopy(DEFAULT_RULES), "map": deepcopy(DEFAULT_MAP)}


def normalize_config(raw: Any) -> dict[str, Any]:
    """Keep only the uploaded map; every gameplay value is canonical."""
    config = default_config()
    if not isinstance(raw, dict):
        return config

    stored_map = raw.get("map")
    if isinstance(stored_map, dict):
        image_data_url = stored_map.get("image_data_url")
        width = stored_map.get("width")
        height = stored_map.get("height")
        valid_dimensions = (
            isinstance(width, int) and not isinstance(width, bool)
            and isinstance(height, int) and not isinstance(height, bool)
            and 1 <= width <= 10_000 and 1 <= height <= 10_000
        )
        if image_data_url is None:
            config["map"] = deepcopy(DEFAULT_MAP)
        elif isinstance(image_data_url, str) and len(image_data_url) <= MAP_IMAGE_MAX_LENGTH and image_data_url.startswith(MAP_IMAGE_PREFIXES) and valid_dimensions:
            config["map"] = {"image_data_url": image_data_url, "width": width, "height": height}
    return config


def rules_for(raw: Any) -> dict[str, Any]:
    return normalize_config(raw)["rules"]
