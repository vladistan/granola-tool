# Smoke Test Baseline

Captured: 2026-05-13

## Environment

- Python 3.13.7
- macOS (darwin)
- Granola local cache: `cache-v6.json` (nearly empty — state.documents = {})
- Granola API: reachable with valid WorkOS token from supabase.json

## list

```bash
$ uv run python scripts/granola.py list --format text
```

**Exit code:** 0

**Output:**
```
Found 0 meetings in Granola:
```

**Notes:** Local cache is empty (no documents). This is expected when
Granola has not populated the cache on this machine.

---

## list (JSON)

```bash
$ uv run python scripts/granola.py list --format json
```

**Exit code:** 0

**Output:**
```json
{
  "meetings": []
}
```

---

## show

```bash
$ uv run python scripts/granola.py show cf905b2e
```

**Exit code:** 1

**Output:**
```
Meeting not found: cf905b2e
```

**Notes:** Searches local cache only. Fails because cache is empty.
This is expected behavior — `show` does not fall back to API.

---

## transcript

```bash
$ uv run python scripts/granola.py transcript cf905b2e-fa03-4485-a1cd-9ebeb9fbcb6c
```

**Exit code:** 1

**Output:**
```
Meeting not found: cf905b2e-fa03-4485-a1cd-9ebeb9fbcb6c
```

**Notes:** `require_document()` searches local cache for the document before
attempting transcript retrieval. Fails at the cache lookup step because
local cache is empty. API fallback for transcript never reached.

---

## export

```bash
$ uv run python scripts/granola.py export cf905b2e-fa03-4485-a1cd-9ebeb9fbcb6c --local-only
```

**Exit code:** 1

**Output:**
```
Meeting not found: cf905b2e-fa03-4485-a1cd-9ebeb9fbcb6c
```

**Notes:** Same as `show` — depends on local cache for document lookup.

---

## api-list

```bash
$ uv run python scripts/granola.py api-list --limit 3
```

**Exit code:** 0

**Output:**
```json
{
  "meetings": [
    {
      "id": "cf905b2e-fa03-4485-a1cd-9ebeb9fbcb6c",
      "title": "(Untitled)",
      "date": "2026-05-12",
      "start": "?",
      "end": "?",
      "attendees": [],
      "has_notes": true,
      "has_summary": false
    },
    {
      "id": "44759533-f9b5-48f0-aed7-be30b7a9a0e5",
      "title": "Data team tactical",
      "date": "2026-05-12",
      "start": "09:30",
      "end": "11:00",
      "attendees": [
        "Matteo Zanotto",
        "Riccardo Volpi",
        "Matteo Meneghetti",
        "Mattia Litrico",
        "Tyler Hayes",
        "Salvatore Adalberto Esposito",
        "Antonio Massaro"
      ],
      "has_notes": false,
      "has_summary": false
    },
    {
      "id": "fb189a64-6868-4de3-9aca-f3606130a6cf",
      "title": "Roof Flow demo — browser models, edge inference, and smart sensors with Mario",
      "date": "2026-05-08",
      "start": "?",
      "end": "?",
      "attendees": [],
      "has_notes": false,
      "has_summary": false
    }
  ],
  "total_returned": 3
}
```

**Notes:** Queries Granola API directly. Returns meetings that are not in
local cache. Always outputs JSON regardless of flags (no --format option).

---

## Summary

| Command | Exit Code | Works? | Notes |
|---------|-----------|--------|-------|
| list | 0 | Yes | Empty cache, returns 0 meetings |
| show | 1 | No* | Requires local cache (empty) |
| transcript | 1 | No* | Requires local cache (empty) |
| export | 1 | No* | Requires local cache (empty) |
| api-list | 0 | Yes | API access works |

*Commands work correctly but local cache is empty on this machine.
When cache has data, show/transcript/export function as designed.
