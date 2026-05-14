"""Granola Tool CLI — Typer application assembly."""

import sys

import typer

from granola_tool.commands.lekhak import lekhak_app
from granola_tool.commands.meeting import meeting_app
from granola_tool.commands.obsidian import obsidian_app
from granola_tool.commands.test_cmd import test_app
from granola_tool.errors import GranolaError, NotFoundError, TokenExpiredError
from granola_tool.monitoring import setup_logging, setup_sentry

app = typer.Typer(
    help="Granola meeting notes CLI — query meetings, export to Obsidian and lekhak.",
    invoke_without_command=True,
)

app.add_typer(meeting_app, name="meeting")
app.add_typer(lekhak_app, name="lekhak")
app.add_typer(obsidian_app, name="obsidian")
app.add_typer(test_app, name="test")


@app.callback()
def default_action(ctx: typer.Context) -> None:
    """Show recent meetings when no command is given."""
    if ctx.invoked_subcommand is None:
        from granola_tool.commands.meeting import meeting_list

        meeting_list(format="text", limit=20)


def main() -> None:
    """Entry point — sets up observability then runs the CLI."""
    setup_logging()
    setup_sentry()
    try:
        app()
    except NotFoundError as e:
        typer.echo(str(e), err=True)
        sys.exit(1)
    except TokenExpiredError as e:
        typer.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
    except GranolaError as e:
        typer.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
