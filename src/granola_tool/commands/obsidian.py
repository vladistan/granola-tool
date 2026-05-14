"""Obsidian command group — export and sync meetings to Obsidian vault."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import structlog
import typer

from granola_tool.config import get_settings
from granola_tool.documents import get_document, list_documents, require_document, _extract_uuid
from granola_tool.errors import NotFoundError
from granola_tool.render import format_time

obsidian_app = typer.Typer(help="Export and sync meetings to Obsidian vault.", no_args_is_help=True)


@dataclass
class _ExportData:
    doc_id: str
    note_id: str
    title: str
    created_dash: str
    participant_names: list[str]
    duration: str | None
    summary: str
    notes_md: str
    utterances: list[dict[str, Any]] | None


def _compute_meeting_duration(
    utterances: list[dict[str, Any]] | None, start: str | None, end: str | None
) -> str | None:
    if not start or not end:
        if not utterances:
            return None
        times = [u.get("start_time", "") for u in utterances if u.get("start_time")]
        if len(times) < 2:
            return None
        start, end = times[0], times[-1]
    try:
        t0 = datetime.fromisoformat(start.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(end.replace("Z", "+00:00"))
        mins = int((t1 - t0).total_seconds() / 60)
        return f"{mins // 60:02d}:{mins % 60:02d}"
    except (ValueError, TypeError):
        return None


def _generate_filename(title: str, created_date: str) -> str:
    slug = title.lower().strip()
    for ch in ".,!?:;'\"()[]{}":
        slug = slug.replace(ch, "")
    slug = slug.replace(" ", "-").replace("--", "-")[:60].rstrip("-")
    return f"{created_date}-{slug}.md"


def _build_markdown(data: _ExportData) -> str:
    lines: list[str] = ["---"]
    lines.append(f"granola_id: {data.doc_id}")
    lines.append(f"note_id: {data.note_id}")
    lines.append(f'title: "{data.title}"')
    lines.append(f"date: {data.created_dash}")
    if data.participant_names:
        lines.append(f"participants: {json.dumps(data.participant_names)}")
    if data.duration:
        lines.append(f"duration: {data.duration}")
    lines.append("source: granola")
    lines.append("---")
    lines.append("")
    lines.append(f"# {data.title}")
    lines.append("")

    if data.notes_md:
        lines.extend(["## Notes", "", data.notes_md, ""])

    if data.utterances:
        lines.extend(["## Transcript", ""])
        for u in data.utterances:
            text = u.get("text", "").strip()
            if not text:
                continue
            speaker_info = u.get("speaker", {})
            source = speaker_info.get("source", "") if isinstance(speaker_info, dict) else ""
            speaker = data.participant_names[0] if source == "microphone" and data.participant_names else "Other"
            lines.append(f"**{speaker}**: {text}")
            lines.append("")

    return "\n".join(lines)


@obsidian_app.command("export")
def obsidian_export(
    meeting_id: Annotated[str, typer.Argument(help="Meeting ID (prefix) or title substring")],
    vault: Annotated[str | None, typer.Option("--vault", help="Obsidian vault path")] = None,
    output: Annotated[str | None, typer.Option("--output", help="Custom output path")] = None,
) -> None:
    """Export a meeting to Obsidian note (Fathom-compatible format)."""
    log = structlog.get_logger()
    settings = get_settings()
    vault_path = vault or str(settings.vault_path)

    try:
        doc = require_document(meeting_id)
    except NotFoundError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(code=1) from None

    full = get_document(doc["id"])
    granola_uuid = _extract_uuid(full)
    title: str = full.get("title") or "(Untitled)"
    created_dash: str = full.get("created_at", "")[:10]
    created: str = created_dash.replace("-", "")

    attendees = full.get("attendees", [])
    participant_names = [a.get("name", "") for a in attendees if a.get("name")]
    utterances = full.get("transcript", [])
    notes_md = full.get("summary_markdown") or ""

    cal = full.get("calendar_event") or {}
    start = cal.get("scheduled_start_time")
    end = cal.get("scheduled_end_time")
    duration = _compute_meeting_duration(utterances or None, start, end)

    export_data = _ExportData(
        doc_id=granola_uuid,
        note_id=full.get("id", ""),
        title=title,
        created_dash=created_dash,
        participant_names=participant_names,
        duration=duration,
        summary="",
        notes_md=notes_md,
        utterances=utterances or None,
    )
    content = _build_markdown(export_data)

    filename = _generate_filename(title, created)
    out_path = Path(output) if output else Path(vault_path).expanduser() / filename

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
    except OSError as e:
        typer.echo(f"ERROR: could not write output file: {e}", err=True)
        raise typer.Exit(code=4) from None

    log.info("meeting_exported", path=str(out_path), title=title)
    print(
        json.dumps(
            {
                "exported": str(out_path),
                "title": title,
                "date": created,
                "participants": participant_names,
                "duration": duration,
                "utterances": len(utterances) if utterances else 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@obsidian_app.command("sync")
def obsidian_sync(
    vault: Annotated[str | None, typer.Option("--vault", help="Obsidian vault path")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max meetings to check")] = 20,
) -> None:
    """Sync recent meetings to Obsidian vault (export new ones)."""
    log = structlog.get_logger()
    settings = get_settings()
    vault_path = Path(vault or str(settings.vault_path)).expanduser()

    if not vault_path.exists():
        typer.echo(f"ERROR: vault not found: {vault_path}", err=True)
        raise typer.Exit(code=1)

    known_ids: set[str] = set()
    for md_file in vault_path.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            for line in content.splitlines()[:10]:
                if line.startswith("granola_id: "):
                    known_ids.add(line.removeprefix("granola_id: ").strip())
                elif line.startswith("note_id: "):
                    known_ids.add(line.removeprefix("note_id: ").strip())
        except OSError:
            continue

    docs = list_documents(limit=limit)
    exported = 0
    skipped = 0

    for doc in docs:
        uuid = _extract_uuid(doc)
        note_id = doc.get("id", "")
        if uuid in known_ids or note_id in known_ids:
            skipped += 1
            continue
        try:
            full = get_document(doc["id"])
            granola_uuid = _extract_uuid(full)
            title = full.get("title") or "(Untitled)"
            created_dash = full.get("created_at", "")[:10]
            created = created_dash.replace("-", "")
            attendees = full.get("attendees", [])
            participant_names = [a.get("name", "") for a in attendees if a.get("name")]
            utterances = full.get("transcript", [])
            notes_md = full.get("summary_markdown") or ""
            cal = full.get("calendar_event") or {}
            duration = _compute_meeting_duration(
                utterances or None, cal.get("scheduled_start_time"), cal.get("scheduled_end_time")
            )

            export_data = _ExportData(
                doc_id=granola_uuid,
                note_id=full.get("id", ""),
                title=title,
                created_dash=created_dash,
                participant_names=participant_names,
                duration=duration,
                summary="",
                notes_md=notes_md,
                utterances=utterances or None,
            )
            content = _build_markdown(export_data)
            filename = _generate_filename(title, created)
            out_path = vault_path / filename
            out_path.write_text(content, encoding="utf-8")
            exported += 1
            log.info("meeting_synced", meeting_id=uuid)
        except Exception as e:
            log.warning("sync_export_failed", meeting_id=uuid, error=str(e))

    print(json.dumps({"exported": exported, "skipped": skipped, "total_checked": len(docs)}, indent=2))
