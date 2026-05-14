# granola-tool

CLI tool for querying [Granola](https://granola.ai) meeting recordings, viewing AI-generated notes and transcripts, and exporting to Obsidian and a local knowledge base.

Inspired by [glebis/claude-skills/granola](https://github.com/glebis/claude-skills/tree/main/granola).

## Prerequisites

- macOS with Granola desktop app (Business or Enterprise plan)
- Python >= 3.13
- uv package manager
- API key: Granola app → Settings → Connectors → API keys

## Installation

```bash
cd granola-tool
uv sync
export GRANOLA_KEY="grn_your_api_key_here"
uv run granola-tool test api   # verify setup
```

## Commands

```
granola-tool                        # show recent meetings (default)
granola-tool meeting list           # list meetings with short IDs
granola-tool meeting notes <id>     # view AI-generated notes
granola-tool meeting transcript <id> # view transcript

granola-tool lekhak list [folder]   # browse knowledge base
granola-tool lekhak record <id> <folder>  # export meeting
granola-tool lekhak sync            # find unrecorded meetings
granola-tool lekhak show <slug>     # view exported content
granola-tool lekhak edit <slug>     # open in $EDITOR

granola-tool obsidian export <id>   # export to Obsidian vault
granola-tool obsidian sync          # batch export new meetings

granola-tool test token             # check API key
granola-tool test api               # test connectivity
granola-tool test config            # show configuration
```

See `SKILL.md` for full command reference with all options.

## Meeting IDs

Meetings can be referenced by:
- Short ID from list output (e.g., `HNWQ`)
- Full note ID (e.g., `not_HNWQaVwnQVhGMk`)
- UUID from desktop app (e.g., `44759533-...`)
- Title substring (e.g., `"team sync"`)

## Configuration

Environment variables (`GRANOLA_*` prefix):

| Variable | Default | Description |
|----------|---------|-------------|
| `GRANOLA_KEY` | (required) | API key |
| `GRANOLA_API_BASE` | `https://public-api.granola.ai` | API endpoint |
| `GRANOLA_VAULT_PATH` | `~/Documents/ObsidianVault` | Obsidian vault path |
| `GRANOLA_LEKHAK_PATH` | `~/knowledge-base/meetings` | Local knowledge base path |

## For AI Agents (Claude Code)

This tool is designed to work with both human users and AI agents.
To configure it as a Claude Code skill:

1. Copy `SKILL.md` to your Claude Code skills directory (`.claude/skills/`)
2. The skill provides structured access to all CLI commands
3. Agents can invoke meeting, obsidian, and lekhak commands programmatically

The skill document includes the full command reference, configuration details,
and typical workflows that agents can follow to query meetings, export notes,
and manage a local knowledge base.

## Development

```bash
uv run ruff check src/
uv run mypy src/
uv run pytest
```

## License

MIT — see [LICENSE](LICENSE).
