"""Cache path discovery and loading."""

import glob
import json
from pathlib import Path
from typing import Any

import structlog

from granola_tool.errors import CacheError

_FALLBACK_GRANOLA_DIR = Path.home() / "Library" / "Application Support" / "Granola"


def get_cache_path(cache_dir: Path | None = None) -> Path:
    """Find the latest cache-v*.json file."""
    log = structlog.get_logger()
    directory = cache_dir or _FALLBACK_GRANOLA_DIR
    candidates = glob.glob(str(directory / "cache-v*.json"))
    candidates = [c for c in candidates if not c.endswith(".tmp")]
    if not candidates:
        raise CacheError("No Granola cache file found. Is Granola installed?")
    candidates.sort(
        key=lambda p: int(Path(p).name.split("-v")[1].split(".json")[0]),
        reverse=True,
    )
    path = Path(candidates[0])
    log.debug("cache_path_resolved", path=str(path))
    return path


def load_cache(cache_path: Path | None = None) -> dict[str, Any]:
    """Load and parse Granola cache file."""
    path = cache_path or get_cache_path()
    with open(path) as f:
        raw = json.load(f)
    state = raw.get("cache", {})
    if isinstance(state.get("state"), str):
        parsed: dict[str, Any] = json.loads(state["state"])
    else:
        parsed = state.get("state", {})
    return parsed


