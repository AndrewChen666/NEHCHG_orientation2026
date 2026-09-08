"""Settlement for market ownership income.

Ownership is paid in whole minutes while active. When ownership ends, the
remaining partial minute is rounded half-up exactly as the game sheet states.
"""

from typing import Any

from .game_clock import effective_elapsed_ms


def _earned_minutes(started_elapsed_ms: int, elapsed_ms: int, final: bool) -> int:
    duration_ms = max(0, elapsed_ms - started_elapsed_ms)
    return (duration_ms + 30_000) // 60_000 if final else duration_ms // 60_000


async def settle_ownership(
    connection: Any,
    session: Any,
    *,
    market_id: Any | None = None,
    final: bool = False,
    actor_id: Any | None = None,
) -> int:
    """Credit unrecorded ownership income and return the credited coin total."""
    elapsed = effective_elapsed_ms(session)
    query = """
        SELECT id, team_id, started_elapsed_ms, rate_per_minute, paid_minutes
        FROM market_ownership
        WHERE session_id = $1 AND ended_at IS NULL
    """
    arguments: list[Any] = [session["id"]]
    if market_id is not None:
        query += " AND market_id = $2"
        arguments.append(market_id)
    rows = await connection.fetch(query, *arguments)
    credited = 0
    for ownership in rows:
        earned_minutes = _earned_minutes(int(ownership["started_elapsed_ms"]), elapsed, final)
        delta_minutes = max(0, earned_minutes - int(ownership["paid_minutes"] or 0))
        if not delta_minutes:
            continue
        amount = delta_minutes * int(ownership["rate_per_minute"])
        await connection.execute(
            "UPDATE market_ownership SET paid_minutes = paid_minutes + $1 WHERE id = $2",
            delta_minutes,
            ownership["id"],
        )
        await connection.execute(
            "UPDATE team_wallets SET balance = balance + $1, updated_at = NOW() WHERE team_id = $2",
            amount,
            ownership["team_id"],
        )
        await connection.execute(
            """
            INSERT INTO money_ledger (session_id, team_id, amount, reason, reference_id, created_by)
            VALUES ($1, $2, $3, 'market_ownership_income', $4, $5)
            """,
            session["id"],
            ownership["team_id"],
            amount,
            ownership["id"],
            actor_id,
        )
        credited += amount
    return credited


async def close_active_ownership(connection: Any, session: Any, market_id: Any, actor_id: Any | None = None) -> int:
    """Settle and close a market before another team takes it."""
    elapsed = effective_elapsed_ms(session)
    credited = await settle_ownership(connection, session, market_id=market_id, final=True, actor_id=actor_id)
    await connection.execute(
        "UPDATE market_ownership SET ended_at = NOW(), ended_elapsed_ms = $1 WHERE market_id = $2 AND ended_at IS NULL",
        elapsed,
        market_id,
    )
    return credited
