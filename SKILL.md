---
name: granola
description: Query Granola meeting recordings, view AI-generated notes and transcripts, export to Obsidian vault and lekhak knowledge base. Uses official Granola public API with persistent API key.
---

# Granola Meeting Tool

Query Granola meetings, view AI notes and transcripts, export to Obsidian and lekhak knowledge base.

## Prerequisites

- Granola desktop app (macOS) with Business or Enterprise plan
- API key: Granola app → Settings → Connectors → API keys
- Set `GRANOLA_KEY` env var with the key

## Setup

```bash
cd granola-tool
uv sync
uv run granola-tool test token    # verify key
uv run granola-tool test api      # verify connectivity
```

## Command Reference

### `meeting` — Query Granola meetings

```
granola-tool meeting list [-n LIMIT] [-f text|json]
granola-tool meeting notes <id> [-f text|json]
granola-tool meeting transcript <id> [-f text|json]
```

| Command | Description |
|---------|-------------|
| `meeting list` | List recent meetings (table with short IDs, friendly dates) |
| `meeting notes <id>` | Show AI-generated meeting notes and attendees |
| `meeting transcript <id>` | Show full transcript with timestamps |

No subcommand → shows meeting list by default.

### `lekhak` — Manage lekhak knowledge base

```
granola-tool lekhak list [name]
granola-tool lekhak show <slug> [-t]
granola-tool lekhak edit <slug> [-t]
granola-tool lekhak record <id> <name> [--create] [--notes-only] [--transcript-only]
granola-tool lekhak sync [-n LIMIT]
granola-tool lekhak reconcile <name> [-n LIMIT] [--dry-run]
granola-tool lekhak enrich <name>
```

| Command | Description |
|---------|-------------|
| `lekhak list` | List all meeting folders with session counts |
| `lekhak list <name>` | List sessions in a folder (slug, summary/transcript status, title) |
| `lekhak show <slug>` | Show contents (latest if just name, specific if `name/MM-DD-YY`) |
| `lekhak show <slug> -t` | Show transcript instead of notes |
| `lekhak edit <slug>` | Open notes in `$EDITOR` |
| `lekhak edit <slug> -t` | Open transcript in `$EDITOR` |
| `lekhak record <id> <name>` | Export Granola meeting to lekhak folder |
| `lekhak record <id> <name> --create` | Create new folder if it doesn't exist |
| `lekhak record <id> <name> --notes-only` | Export only AI-generated notes |
| `lekhak record <id> <name> --transcript-only` | Export only transcript |
| `lekhak sync` | Show Granola meetings not yet in lekhak |
| `lekhak reconcile <name>` | Match sessions to Granola IDs (±3 day fuzzy matching) |
| `lekhak reconcile <name> --dry-run` | Preview matches without writing |
| `lekhak enrich <name>` | Add frontmatter to legacy files (extracts metadata from transcript headers) |

### `obsidian` — Export to Obsidian vault

```
granola-tool obsidian export <id> [--vault PATH] [--output PATH]
granola-tool obsidian sync [--vault PATH] [-n LIMIT]
```

| Command | Description |
|---------|-------------|
| `obsidian export <id>` | Export single meeting to vault (Fathom-compatible markdown) |
| `obsidian export <id> --output FILE` | Export to specific file path |
| `obsidian sync` | Batch export new meetings (skips already-exported) |
| `obsidian sync -n 50` | Check more meetings for sync |

### `test` — Infrastructure checks

```
granola-tool test token
granola-tool test api
granola-tool test sentry
granola-tool test config [-f text|json]
```

| Command | Description |
|---------|-------------|
| `test token` | Check API key is set and valid |
| `test api` | Fetch one meeting to verify connectivity |
| `test sentry` | Send test event to Sentry |
| `test config` | Show all configured paths and env vars |

## Meeting IDs

Meetings can be referenced by:
- **Short ID** from `meeting list` output (e.g., `HNWQ`)
- **Full note ID** (e.g., `not_HNWQaVwnQVhGMk`)
- **UUID** from desktop app web URL (e.g., `44759533-...`)
- **Title substring** (e.g., `"team sync"`)

All commands that take `<id>` accept any of these formats.

## Lekhak Slugs

Format: `folder-name/MM-DD-YY` (e.g., `tactical/05-12-26`)

- Used with `lekhak show`, `lekhak edit`
- Just the folder name (e.g., `tactical`) shows the latest session
- Copy slugs directly from `lekhak list <name>` output

## Configuration

All settings overridable via `GRANOLA_*` env vars:

| Env Var | Default | Purpose |
|---------|---------|---------|
| `GRANOLA_KEY` | (required) | API key from Granola app |
| `GRANOLA_API_BASE` | `https://public-api.granola.ai` | API endpoint |
| `GRANOLA_VAULT_PATH` | `~/Documents/ObsidianVault` | Obsidian vault (iCloud) |
| `GRANOLA_LEKHAK_PATH` | `~/knowledge-base/meetings` | Lekhak data directory |

## Typical Workflows

### After a meeting
```bash
granola-tool meeting list                    # find the meeting
granola-tool meeting notes HNWQ              # review AI notes
granola-tool lekhak record HNWQ tactical     # save to knowledge base
```

### Weekly sync
```bash
granola-tool lekhak sync                     # what's new?
granola-tool lekhak record <id> <folder>     # record each missing meeting
```

### First-time setup for a folder
```bash
granola-tool lekhak enrich tactical          # add frontmatter to old files
granola-tool lekhak reconcile tactical -n 300  # match all to Granola IDs
```

## File Formats

### Lekhak (summary: `s/<name>/MM-DD-YY.txt`, transcript: `t/<name>/MM-DD-YY.txt`)

```yaml
---
slug: tactical/05-12-26
granola_id: 44759533-f9b5-48f0-aed7-be30b7a9a0e5
note_id: not_HNWQaVwnQVhGMk
title: Weekly team sync
date: 2026-05-12
participants: [Owner, Alice Smith, ...]
---
[AI-generated notes or Me:/Them: transcript]
```

### Obsidian (`YYYYMMDD-title-slug.md`)

```yaml
---
granola_id: 44759533-f9b5-48f0-aed7-be30b7a9a0e5
note_id: not_HNWQaVwnQVhGMk
title: "Weekly team sync"
date: 2026-05-12
participants: ["Owner", "Alice Smith", ...]
duration: 01:30
source: granola
---
# Weekly team sync
## Notes
[AI-generated notes]
## Transcript
**Speaker**: utterance text
```

## API Details

Uses the official Granola public API (`docs.granola.ai`):
- Auth: `Bearer grn_...` (persistent API key, no expiry)
- List: `GET /v1/notes?page_size=30&cursor=...`
- Detail: `GET /v1/notes/{id}?include=transcript`
- Rate limit: 5 req/sec sustained, burst 25 in 5s
- Pagination: cursor-based (automatic in tool)
- Two ID types: `granola_id` (UUID from desktop app) and `note_id` (API format: `not_*`)

## Known Limitations

- Personal API key only sees notes you own or shared with you directly
- Workspace/team space notes require Enterprise API key (admin-created)
- No per-utterance speaker names — only "microphone" vs "speaker" source
- Meetings without AI-generated summaries don't appear in the API
- Rate limited to 5 req/sec — batch operations respect this automatically
