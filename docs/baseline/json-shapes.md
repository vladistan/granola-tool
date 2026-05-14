# JSON Output Shapes — Baseline

Captured: 2026-05-13

## list --format json

```json
{
  "meetings": [
    {
      "id": "<uuid>",
      "title": "<string>",
      "created_at": "<iso-datetime>",
      "attendees": ["<name>", ...],
      "has_notes": <bool>,
      "calendar": {
        "title": "<string>",
        "start": "<iso-datetime>",
        "end": "<iso-datetime>"
      } | null
    }
  ]
}
```

**Notes:** When cache is empty, `meetings` is an empty array `[]`.

---

## api-list

Always outputs JSON (no --format flag).

```json
{
  "meetings": [
    {
      "id": "<uuid>",
      "title": "<string>",
      "date": "<YYYY-MM-DD>",
      "start": "<HH:MM>" | "?",
      "end": "<HH:MM>" | "?",
      "attendees": ["<name>", ...],
      "has_notes": <bool>,
      "has_summary": <bool>
    }
  ],
  "total_returned": <int>
}
```

**Differences from `list --format json`:**
- `api-list` has `date` (date only) vs `list` has `created_at` (full datetime)
- `api-list` has `start`/`end` as time strings ("HH:MM" or "?")
- `api-list` has `has_summary` field
- `api-list` has `total_returned` count at top level
- `api-list` lacks `calendar` object

---

## show (JSON)

Output shape (observed from code inspection — cache empty prevents live capture):

```json
{
  "id": "<uuid>",
  "title": "<string>",
  "date": "<YYYY-MM-DD>",
  "attendees": [
    {"name": "<string>", "email": "<string>"}
  ],
  "calendar": {
    "title": "<string>",
    "start": "<iso-datetime>",
    "end": "<iso-datetime>"
  } | null,
  "notes_markdown": "<string>",
  "notes_plain": "<string>",
  "summary": "<string>"
}
```

---

## transcript --format json

Output shape (from code inspection):

```json
[
  {
    "start_timestamp": "<iso-datetime>",
    "end_timestamp": "<iso-datetime>",
    "text": "<string>",
    "source": "<string>"
  }
]
```

**Notes:** Transcript is a flat array of utterance objects. Each has timestamps,
text content, and an optional source indicator.

---

## transcript --format text

```
[HH:MM] [source] text content here
[HH:MM] [source] more text here
```

Not JSON — plain text with timestamp and source prefix per line.

---

## export

Outputs Obsidian markdown (not JSON). No --format flag.

```markdown
---
date: <YYYY-MM-DD>
duration: <HH:MM>
people: [name1, name2]
---

# <title>

## People

- name1
- name2 (email@example.com)

## Notes

<notes_markdown content>

## Transcript

[HH:MM] [source] text
...
```

---

## Inconsistencies Noted

1. **Date field naming**: `list` uses `created_at` (ISO datetime), `api-list` uses `date` (date only), `show` uses `date` (date only)
2. **Attendees format**: `list` and `api-list` return flat string arrays `["name"]`, `show` returns objects `[{"name": ..., "email": ...}]`
3. **api-list always JSON**: No `--format` option, always outputs JSON. `list` respects `--format text|json`
4. **No --format for show**: `show` always outputs JSON (implicit)
5. **start/end fields**: `api-list` uses "?" for unknown times; other commands use null or omit
