"""Granola API client — official public API with API key auth."""

import json
import urllib.request
from typing import Any

import structlog

from granola_tool.config import get_settings
from granola_tool.errors import ApiError


def api_request(endpoint: str, params: dict[str, str] | None = None) -> Any:
    """Make authenticated GET request to Granola public API."""
    log = structlog.get_logger()
    settings = get_settings()

    if not settings.key:
        raise ApiError("No API key configured. Set GRANOLA_KEY or GRANOLA_API_KEY env var.")

    url = f"{settings.api_base}{endpoint}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items() if v)
        url = f"{url}?{query}"

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {settings.key}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            return json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        log.error("api_request_failed", endpoint=endpoint, status=e.code, body=body[:200])
        raise ApiError(f"API request to {endpoint} failed: {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        log.error("api_request_failed", endpoint=endpoint, error=str(e))
        raise ApiError(f"API request to {endpoint} failed: {e}") from e
