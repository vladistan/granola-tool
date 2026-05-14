# Contributing to granola-tool

## Development Setup

### Prerequisites

- Python >= 3.13
- uv package manager
- macOS with Granola desktop app (for smoke tests)

### Initial Setup

```bash
cd granola-tool

# Install all dependencies including dev tools
uv sync

# Install pre-commit hooks (configured at repo root)
pre-commit install

# Verify installation
uv run granola-tool --help
```

### Environment Configuration

The tool reads credentials from the Granola app automatically. For Sentry error tracking:

```bash
export SENTRY_DSN=your_dsn_here
```

**Never commit credentials.** Use environment variables or a local `.envrc` (not committed).

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_cli.py

# Verbose output
uv run pytest -v
```

### Code Quality

Before committing, all quality checks must pass:

```bash
# Lint
uv run ruff check src tests

# Auto-fix lint issues
uv run ruff check --fix src tests

# Format
uv run ruff format src tests

# Type checking (source only)
uv run mypy src

# Run pre-commit hooks on staged files
pre-commit run --files $(git diff --cached --name-only)
```

**Quality Gate:** All of the following must pass before committing:
- `pytest` — all tests pass
- `ruff check` — no lint violations
- `ruff format --check` — no formatting issues
- `mypy --strict src/` — no type errors
- `pre-commit` — all hooks pass

### Adding Dependencies

```bash
# Add runtime dependency
uv add package-name

# Add dev-only dependency
uv add --group dev package-name

# Update all dependencies
uv sync --upgrade
```

Always commit `uv.lock` after changing dependencies.

## Code Style

- Type annotations on all function signatures (mypy strict enforced)
- Structured logging via `structlog` — never use `print()` for diagnostics
- User-facing output to stdout; logs and errors to stderr
- Typed exceptions in `errors.py`; only `cli.py` translates to exit codes

### CLI Command Structure

```python
@app.command()
def my_command(
    arg: Annotated[str, typer.Argument(help="Argument description")],
    option: Annotated[str, typer.Option("--option", "-o", help="Option description")] = "default",
) -> None:
    """Brief command description."""
    ...
```

### Error Handling

- Define typed exceptions in `errors.py`
- Helper functions raise exceptions; `cli.py` catches and exits
- Log context before raising: `logger.error("...", error=str(e))`
- Never expose stack traces to users (use `--debug` flag pattern)

## Testing

- Use `typer.testing.CliRunner` for CLI integration tests
- Aim for > 80% coverage
- Test both success and error paths
- Smoke tests against real Granola data run manually (require live token)

## Commit Message Format

```
type: brief description (50 chars max)

Longer description explaining why, not what.
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

## License

By contributing, you agree your contributions will be licensed under the MIT License.
