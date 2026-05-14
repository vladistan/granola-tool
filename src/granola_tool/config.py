"""Typed configuration via pydantic-settings."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class GranolaSettings(BaseSettings):
    """Granola tool configuration — all fields overridable via GRANOLA_* env vars."""

    key: str = ""
    api_base: str = "https://public-api.granola.ai"
    vault_path: Path = Path(os.path.expanduser("~/Documents/ObsidianVault"))
    lekhak_path: Path = Path(os.path.expanduser("~/knowledge-base/meetings"))
    cache_dir: Path = Path(os.path.expanduser("~/Library/Application Support/Granola"))

    model_config = {"env_prefix": "GRANOLA_"}


_settings: GranolaSettings | None = None


def get_settings() -> GranolaSettings:
    """Get or create the singleton settings instance."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = GranolaSettings()
    return _settings
