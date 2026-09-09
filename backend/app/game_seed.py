"""Idempotent fixed-data seeding for pre-existing 活米村 sessions."""

import json
from typing import Any

from .game_config import DEFAULT_BLACK_MARKET_CARDS, MARKET_CODES, default_rates


async def ensure_fixed_game_data(connection: Any, session_id: Any) -> None:
    """Make a pre-game session use the published market sheet and card deck.

    New sessions receive these rows at bootstrap. This small, idempotent repair
    is for sessions created before the rule sheet was locked in code. It is
    deliberately only called while a session is still draft or scheduled, so
    historic cards and transactions are never rewritten mid-game.
    """
    markets = await connection.fetch(
        "SELECT id, code FROM markets WHERE session_id = $1",
        session_id,
    )
    market_ids = {market["code"]: market["id"] for market in markets}
    if set(market_ids) != set(MARKET_CODES):
        return

    for rate in default_rates():
        await connection.execute(
            """
            INSERT INTO market_rates (market_id, period, resource_type, buy_price, sell_price, is_public)
            VALUES ($1, $2, $3, $4, $5, TRUE)
            ON CONFLICT (market_id, period, resource_type)
            DO UPDATE SET buy_price = EXCLUDED.buy_price,
                          sell_price = EXCLUDED.sell_price,
                          is_public = TRUE
            """,
            market_ids[rate["market_code"]],
            rate["period"],
            rate["resource_type"],
            rate["buy_price"],
            rate["sell_price"],
        )

    effect_count = await connection.fetchval(
        "SELECT COUNT(*) FROM black_market_effects WHERE session_id = $1",
        session_id,
    )
    if effect_count:
        return
    await connection.execute("DELETE FROM black_market_cards WHERE session_id = $1", session_id)
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
