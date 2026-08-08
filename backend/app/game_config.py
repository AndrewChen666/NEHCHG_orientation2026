from copy import deepcopy
import re
from typing import Any


RESOURCE_TYPES = ("dragon_egg", "time_device", "unicorn_blood", "basilisk_fang")
TEAM_COUNT = 8
TEAM_TONES = ("aurora", "ignis", "terra", "aqua", "nova", "solis", "ventus", "luna")
PRODUCT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
MAP_IMAGE_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/webp;base64,",
)
MAP_IMAGE_MAX_LENGTH = 9_000_000

DEFAULT_PRODUCTS: list[dict[str, Any]] = [
    {"key": "dragon_egg", "name": "A", "short_name": "A", "unit_name": "個"},
    {"key": "time_device", "name": "B", "short_name": "B", "unit_name": "個"},
    {"key": "unicorn_blood", "name": "C", "short_name": "C", "unit_name": "瓶"},
    {"key": "basilisk_fang", "name": "D", "short_name": "D", "unit_name": "根"},
]

DEFAULT_TEAM_PROFILES: list[dict[str, Any]] = [
    {"name": "葛萊芬多", "english_name": "GRYFFINDOR", "icon": "♜", "description": "勇氣與膽識", "tone": "ignis"},
    {"name": "雷文克勞", "english_name": "RAVENCLAW", "icon": "✦", "description": "智慧與學習", "tone": "aurora"},
    {"name": "赫夫帕夫", "english_name": "HUFFLEPUFF", "icon": "☼", "description": "忠誠與團結", "tone": "solis"},
    {"name": "史萊哲林", "english_name": "SLYTHERIN", "icon": "⌁", "description": "企圖與韌性", "tone": "terra"},
    {"name": "星耀院", "english_name": "NOVA", "icon": "✧", "description": "好奇與創造", "tone": "nova"},
    {"name": "日冕院", "english_name": "SOLIS", "icon": "☼", "description": "熱情與專注", "tone": "solis"},
    {"name": "風行院", "english_name": "VENTUS", "icon": "◇", "description": "自由與協作", "tone": "ventus"},
    {"name": "月影院", "english_name": "LUNA", "icon": "☽", "description": "觀察與直覺", "tone": "luna"},
]

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


def default_config() -> dict[str, Any]:
    return {
        "products": deepcopy(DEFAULT_PRODUCTS),
        "rules": deepcopy(DEFAULT_RULES),
        "map": deepcopy(DEFAULT_MAP),
    }


def normalize_config(raw: Any) -> dict[str, Any]:
    """Merge stored JSON with safe defaults so older sessions keep working."""
    config = default_config()
    if not isinstance(raw, dict):
        return config

    stored_products = raw.get("products")
    if (
        isinstance(stored_products, list)
        and len(stored_products) == len(DEFAULT_PRODUCTS)
        and all(
            isinstance(item, dict)
            and isinstance(item.get("key"), str)
            and PRODUCT_KEY_PATTERN.fullmatch(item["key"])
            and isinstance(item.get("name"), str)
            and isinstance(item.get("short_name"), str)
            and isinstance(item.get("unit_name"), str)
            for item in stored_products
        )
        and len({item["key"] for item in stored_products}) == len(stored_products)
    ):
        config["products"] = [
            {
                "key": item["key"],
                "name": item["name"],
                "short_name": item["short_name"],
                "unit_name": item["unit_name"],
            }
            for item in stored_products
        ]

    stored_rules = raw.get("rules")
    if isinstance(stored_rules, dict):
        config["rules"].update({key: value for key, value in stored_rules.items() if key in DEFAULT_RULES})

    rewards = config["rules"].get("magic_reward_by_difficulty")
    if not isinstance(rewards, list) or len(rewards) != 5:
        config["rules"]["magic_reward_by_difficulty"] = deepcopy(DEFAULT_RULES["magic_reward_by_difficulty"])

    stored_map = raw.get("map")
    if isinstance(stored_map, dict):
        image_data_url = stored_map.get("image_data_url")
        width = stored_map.get("width")
        height = stored_map.get("height")
        valid_dimensions = (
            isinstance(width, int)
            and not isinstance(width, bool)
            and isinstance(height, int)
            and not isinstance(height, bool)
            and 1 <= width <= 10_000
            and 1 <= height <= 10_000
        )
        if image_data_url is None:
            config["map"] = deepcopy(DEFAULT_MAP)
        elif (
            isinstance(image_data_url, str)
            and len(image_data_url) <= MAP_IMAGE_MAX_LENGTH
            and image_data_url.startswith(MAP_IMAGE_PREFIXES)
            and valid_dimensions
        ):
            config["map"] = {"image_data_url": image_data_url, "width": width, "height": height}
    return config


def rules_for(raw: Any) -> dict[str, Any]:
    return normalize_config(raw)["rules"]
