"""Shared test fixtures."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from granola_tool.cli import app
from granola_tool.monitoring import setup_logging

setup_logging()

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_app():
    return app


@pytest.fixture
def fixture_path() -> Path:
    return FIXTURES


@pytest.fixture
def string_state_path() -> Path:
    return FIXTURES / "cache_string_state.json"


@pytest.fixture
def object_state_path() -> Path:
    return FIXTURES / "cache_object_state.json"


@pytest.fixture
def patch_cache_path(monkeypatch, string_state_path):
    """Patch get_cache_path to return the string_state fixture."""
    import granola_tool.cache  # noqa: PLC0415

    monkeypatch.setattr(granola_tool.cache, "get_cache_path", lambda: string_state_path)
