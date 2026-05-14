"""Output formatting and time utilities."""

from datetime import datetime
from typing import Any


def format_time(iso_str: str | None) -> str:
    """Format ISO timestamp to HH:MM."""
    if not iso_str:
        return "?"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%H:%M")
    except (ValueError, TypeError):
        return "?"


def compute_duration(utterances: list[dict[str, Any]]) -> str | None:
    """Compute duration from first to last utterance timestamps."""
    if not utterances:
        return None
    first_ts: str = utterances[0].get("start_timestamp", "")
    last_ts: str = utterances[-1].get("end_timestamp", "")
    if not first_ts or not last_ts:
        return None
    try:
        t0 = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        delta = t1 - t0
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes // 60:02d}:{minutes % 60:02d}"
    except (ValueError, TypeError):
        return None
