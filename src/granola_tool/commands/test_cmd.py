"""Test command group — verify infrastructure connectivity."""

import json
from typing import Annotated

import typer

from granola_tool.config import get_settings

test_app = typer.Typer(help="Test infrastructure connectivity and configuration.", no_args_is_help=True)


@test_app.command("token")
def test_token() -> None:
    """Check API key validity."""
    settings = get_settings()
    if not settings.key:
        typer.echo("FAIL: No API key configured", err=True)
        typer.echo("  Set GRANOLA_KEY or GRANOLA_API_KEY env var", err=True)
        raise typer.Exit(code=1)

    key = settings.key
    prefix = key[:10] if len(key) > 10 else key[:4]
    print(f"OK: API key configured ({prefix}...)")
    print(f"  Length: {len(key)} chars")
    print(f"  Base URL: {settings.api_base}")


@test_app.command("api")
def test_api() -> None:
    """Test API connectivity by fetching one meeting."""
    from granola_tool.api import api_request
    from granola_tool.errors import ApiError

    try:
        result = api_request("/v1/notes", {"page_size": "1"})
        notes = result.get("notes", [])
        print(f"OK: API reachable, got {len(notes)} note(s)")
        if notes:
            print(f"  Latest: {notes[0].get('title', '(Untitled)')}")
        has_more = result.get("hasMore", False)
        print(f"  Has more: {has_more}")
    except ApiError as e:
        typer.echo(f"FAIL: {e}", err=True)
        raise typer.Exit(code=1) from None


@test_app.command("sentry")
def test_sentry() -> None:
    """Test Sentry integration by sending a test event."""
    import sentry_sdk

    dsn = sentry_sdk.Hub.current.client.dsn if sentry_sdk.Hub.current.client else None
    if not dsn:
        typer.echo("SKIP: Sentry not initialized (no DSN configured)")
        return

    print("OK: Sentry configured")
    print(f"  DSN: {str(dsn)[:40]}...")
    sentry_sdk.capture_message("granola-tool test event", level="info")
    print("  Test event sent")


@test_app.command("config")
def test_config(
    format: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "text",
) -> None:
    """Show current configuration and paths."""
    settings = get_settings()
    key_display = f"{settings.key[:10]}..." if settings.key else "(not set)"
    config = {
        "api_key": key_display,
        "api_base": settings.api_base,
        "vault_path": str(settings.vault_path),
        "lekhak_path": str(settings.lekhak_path),
    }

    if format == "json":
        print(json.dumps(config, indent=2))
    else:
        print("Current configuration:")
        print(f"  API key:     {config['api_key']}")
        print(f"  API base:    {config['api_base']}")
        print(f"  Vault path:  {config['vault_path']}")
        print(f"  Lekhak path: {config['lekhak_path']}")
        print()
        print("Override with GRANOLA_* env vars:")
        print("  GRANOLA_KEY, GRANOLA_API_BASE, GRANOLA_VAULT_PATH, GRANOLA_LEKHAK_PATH")
