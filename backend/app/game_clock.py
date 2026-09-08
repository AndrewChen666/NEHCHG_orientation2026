"""Server-side clock helpers shared by every game action."""

from datetime import datetime, timezone
from typing import Any


def effective_elapsed_ms(row: Any) -> int:
    started_at = row["started_at"]
    if started_at is None:
        return 0
    end_at = row["paused_at"] or datetime.now(timezone.utc)
    pause_ms = int(row["accumulated_pause_ms"] or 0)
    return max(0, int((end_at - started_at).total_seconds() * 1000) - pause_ms)


def period_for_elapsed(elapsed_ms: int, rules: dict[str, Any]) -> int:
    """Return the live 1–4 period, or 0 before/after the 60-minute game."""
    period_count = int(rules["period_count"])
    period_ms = int(rules["period_duration_minutes"]) * 60_000
    if elapsed_ms < 0 or elapsed_ms >= period_count * period_ms:
        return 0
    return elapsed_ms // period_ms + 1


def current_period(row: Any, rules: dict[str, Any]) -> int:
    try:
        manual_override = row["manual_period_override"]
    except KeyError:
        manual_override = None
    if manual_override is not None:
        return int(manual_override)
    return period_for_elapsed(effective_elapsed_ms(row), rules)
