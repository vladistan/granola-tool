"""Meeting command group — interrogate Granola meetings."""

import json
from datetime import datetime
from typing import Annotated, Any

import typer

from granola_tool.documents import get_document, list_documents, require_document, _extract_uuid
from granola_tool.errors import NotFoundError
from granola_tool.render import format_time

meeting_app = typer.Typer(help="Query and explore Granola meetings.", no_args_is_help=True)


def _friendly_date(iso_date: str) -> str:
    """Convert ISO date to human-friendly relative/short format."""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return iso_date[:10]
    today = datetime.now().date()
    diff = (today - dt).days
    if diff == 0:
        return "Today"
    if diff == 1:
        return "Yesterday"
    if diff < 7:
        return dt.strftime("%A")
    return dt.strftime("%b %-d")


def _short_id(full_id: str, all_ids: list[str]) -> str:
    """Compute shortest unique prefix (minimum 4 chars)."""
    for length in range(4, len(full_id) + 1):
        prefix = full_id[:length]
        if sum(1 for i in all_ids if i.startswith(prefix)) == 1:
            return prefix
    return full_id[:8]


@meeting_app.command("list")
def meeting_list(
    format: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "text",
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 20,
) -> None:
    """List recent meetings from Granola."""
    docs = list_documents(limit=limit)

    if format == "json":
        output: dict[str, Any] = {"meetings": [], "total_returned": len(docs)}
        for doc in docs:
            cal = doc.get("calendar_event") or {}
            output["meetings"].append(
                {
                    "id": _extract_uuid(doc),
                    "note_id": doc.get("id", ""),
                    "title": doc.get("title") or "(Untitled)",
                    "date": doc.get("created_at", "")[:10],
                    "start": cal.get("scheduled_start_time"),
                    "end": cal.get("scheduled_end_time"),
                    "attendees": [a.get("name", "") for a in doc.get("attendees", [])],
                }
            )
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    if not docs:
        print("No meetings found.")
        return

    all_ids = [d.get("id", "").removeprefix("not_") for d in docs]
    rows: list[tuple[str, str, str, str, str]] = []
    for doc in docs:
        full_id = doc.get("id", "").removeprefix("not_")
        sid = _short_id(full_id, all_ids)
        title = doc.get("title") or "(Untitled)"
        created = doc.get("created_at", "")
        date_str = _friendly_date(created)
        cal = doc.get("calendar_event") or {}
        start = cal.get("scheduled_start_time")
        end = cal.get("scheduled_end_time")
        time_str = ""
        if start:
            s = format_time(start)
            e = format_time(end) if end else ""
            time_str = f"{s}-{e}" if e else s
        attendees_list = doc.get("attendees", [])
        attendees = ", ".join(a.get("name", "") for a in attendees_list[:3])
        if len(attendees_list) > 3:
            attendees += f" +{len(attendees_list) - 3}"
        rows.append((sid, date_str, time_str, title[:50], attendees))

    id_w = max(len(r[0]) for r in rows)
    date_w = max(len(r[1]) for r in rows)
    time_w = max(len(r[2]) for r in rows)
    title_w = max(len(r[3]) for r in rows)

    header = f"{'ID':<{id_w}}  {'DATE':<{date_w}}  {'TIME':<{time_w}}  {'TITLE':<{title_w}}  ATTENDEES"
    print(header)
    print("─" * len(header))
    for sid, date_str, time_str, title, attendees in rows:
        print(f"{sid:<{id_w}}  {date_str:<{date_w}}  {time_str:<{time_w}}  {title:<{title_w}}  {attendees}")


@meeting_app.command("notes")
def meeting_notes(
    meeting_id: Annotated[str, typer.Argument(help="Meeting ID (prefix) or title substring")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "text",
) -> None:
    """Show details of a specific meeting including AI-generated notes."""
    try:
        doc = require_document(meeting_id)
    except NotFoundError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(code=1) from None

    full = get_document(doc["id"])
    notes_md = full.get("summary_markdown") or ""
    attendees = full.get("attendees", [])
    cal = full.get("calendar_event") or {}

    result: dict[str, Any] = {
        "id": _extract_uuid(full),
        "note_id": full.get("id", ""),
        "title": full.get("title") or "(Untitled)",
        "date": full.get("created_at", "")[:10],
        "attendees": attendees,
        "calendar": cal if cal else None,
        "notes": notes_md,
        "web_url": full.get("web_url", ""),
    }

    if format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"# {result['title']}")
        print(f"Date: {result['date']}")
        if attendees:
            names = ", ".join(a.get("name", "") for a in attendees)
            print(f"With: {names}")
        print()
        if notes_md:
            print(notes_md)


@meeting_app.command("transcript")
def meeting_transcript(
    meeting_id: Annotated[str, typer.Argument(help="Meeting ID (prefix) or title substring")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "text",
) -> None:
    """Get transcript for a meeting."""
    try:
        doc = require_document(meeting_id)
    except NotFoundError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(code=1) from None

    full = get_document(doc["id"])
    utterances: list[dict[str, Any]] = full.get("transcript", [])

    if not utterances:
        typer.echo("ERROR: no transcript available for this meeting", err=True)
        raise typer.Exit(code=1)

    if format == "json":
        print(json.dumps(utterances, ensure_ascii=False, indent=2))
    else:
        for u in utterances:
            text: str = u.get("text", "")
            start: str = u.get("start_time", "")
            speaker = u.get("speaker", {})
            source: str = speaker.get("source", "") if isinstance(speaker, dict) else ""
            time_str = format_time(start) if start else ""
            src_tag = f" [{source}]" if source else ""
            print(f"[{time_str}]{src_tag} {text}")
