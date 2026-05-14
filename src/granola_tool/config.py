"""Typed configuration via pydantic-settings."""

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


def _find_config_file() -> Path | None:
    candidates = [
        Path(os.environ["GRANOLA_CONFIG"]) if "GRANOLA_CONFIG" in os.environ else None,
        Path.home() / ".config" / "granola" / "config.toml",
    ]
    for path in candidates:
        if path and path.exists():
            return path
    return None


class _TomlConfigSource(PydanticBaseSettingsSource):
    """Load settings from ~/.config/granola/config.toml (lower priority than env vars)."""

    def get_field_value(self, field: Any, field_name: str) -> Any:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        path = _find_config_file()
        if not path:
            return {}
        with open(path, "rb") as f:
            data = tomllib.load(f)
        result: dict[str, Any] = {}
        if "auth" in data:
            result.update(data["auth"])
        if "paths" in data:
            for key, val in data["paths"].items():
                result[key] = os.path.expanduser(str(val))
        if "api" in data and "base_url" in data["api"]:
            result["api_base"] = data["api"]["base_url"]
        return result


class GranolaSettings(BaseSettings):
    """Granola tool configuration — precedence: env vars > config file > defaults."""

    key: str = ""
    api_base: str = "https://public-api.granola.ai"
    vault_path: Path = Path(os.path.expanduser("~/Documents/ObsidianVault"))
    lekhak_path: Path = Path(os.path.expanduser("~/knowledge-base/meetings"))
    cache_dir: Path = Path(os.path.expanduser("~/Library/Application Support/Granola"))

    model_config = SettingsConfigDict(env_prefix="GRANOLA_", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, env_settings, _TomlConfigSource(settings_cls))


_settings: GranolaSettings | None = None


def get_settings() -> GranolaSettings:
    """Get or create the singleton settings instance."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = GranolaSettings()
    return _settings
