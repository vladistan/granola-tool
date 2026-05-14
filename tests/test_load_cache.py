"""Tests for cache loading."""

from pathlib import Path

from granola_tool.cache import load_cache

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_cache_parses_string_state():
    state = load_cache(cache_path=FIXTURES / "cache_string_state.json")
    assert "documents" in state
    assert "abc-123" in state["documents"]
    assert state["documents"]["abc-123"]["title"] == "Test Meeting"


def test_load_cache_parses_object_state():
    state = load_cache(cache_path=FIXTURES / "cache_object_state.json")
    assert "documents" in state
    assert "def-456" in state["documents"]
    assert state["documents"]["def-456"]["title"] == "Another Meeting"
