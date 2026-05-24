"""Export and manage meetings in the lekhak knowledge base."""

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from granola_tool.config import get_settings
from granola_tool.documents import get_document, require_document, _extract_uuid
from granola_tool.errors import NotFoundError

lekhak_app = typer.Typer(help="Manage meetings in the lekhak knowledge base.", no_args_is_help=True)


def _extract_session_title(filepath: Path) -> str:
    """Extract title from first heading or 'Meeting Title:' line in a file."""
    try:
        for line in filepath.read_text(encoding="utf-8").splitlines()[:20]:
            stripped = line.strip()
            if stripped.startswith("Meeting Title: "):
                return stripped.removeprefix("Meeting Title: ")
            if stripped.startswith("# "):
                return stripped.removeprefix("# ")
            if stripped.startswith("## "):
                return stripped.removeprefix("## ")
            if stripped.startswith("### "):
                return stripped.removeprefix("### ")
            if stripped and not stripped.startswith("-") and not stripped.startswith("─"):
                if ":" in stripped and stripped.split(":")[0].replace("_", "").isalpha():
                    continue
                return stripped
    except OSError:
        pass
    return "n/a"


def _friendly_date(filename: str) -> str:
    """Convert MM-DD-YY.txt filename to readable date."""
    stem = filename.removesuffix(".txt")
    try:
        dt = datetime.strptime(stem, "%m-%d-%y")
        return dt.strftime("%b %-d, %Y")
    except ValueError:
        return stem


def _format_date_header(iso_date: str) -> str:
    """Convert ISO date to short format like 'May 13'."""
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%b %-d")
    except (ValueError, TypeError):
        return iso_date[:10]


def _format_date_filename(iso_date: str) -> str:
    """Convert ISO date to MM-DD-YY filename format."""
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%m-%d-%y")
    except (ValueError, TypeError):
        return "00-00-00"


def _build_frontmatter(
    slug: str,
    title: str,
    date: str,
    participants: list[str],
    granola_id: str = "n/a",
    note_id: str = "n/a",
) -> str:
    """Build YAML frontmatter block."""
    parts = ", ".join(participants) if participants else "n/a"
    lines = [
        "---",
        f"slug: {slug}",
        f"granola_id: {granola_id}",
        f"note_id: {note_id}",
        f"title: {title}",
        f"date: {date}",
        f"participants: [{parts}]",
        "---",
        "",
    ]
    return "\n".join(lines)


def _build_transcript_text(
    title: str, date_header: str, people: list[dict[str, str]], utterances: list[dict[str, Any]]
) -> str:
    """Build transcript in lekhak format: header + Me:/Them: lines."""
    participants = ", ".join(p.get("email") or p.get("name", "") for p in people)
    lines: list[str] = [
        f"Meeting Title: {title}",
        f"Date: {date_header}",
        f"Meeting participants: {participants}",
        "",
        "Transcript:",
        " ",
    ]
    for u in utterances:
        text = u.get("text", "").strip()
        if not text:
            continue
        speaker_info = u.get("speaker", {})
        if isinstance(speaker_info, dict):
            source = speaker_info.get("source", "")
        else:
            source = u.get("source", "")
        speaker = "Me" if source == "microphone" else "Them"
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


@lekhak_app.command("list")
def lekhak_list(
    name: Annotated[str | None, typer.Argument(help="Meeting folder name (omit to list all)")] = None,
    base_dir: Annotated[str, typer.Option("--dir", help="Lekhak granola data dir")] = "",
) -> None:
    """List meetings and dates in the lekhak knowledge base."""
    settings = get_settings()
    base = Path(base_dir) if base_dir else settings.lekhak_path
    summary_root = base / "s"

    if not summary_root.exists():
        typer.echo("ERROR: lekhak granola directory not found", err=True)
        raise typer.Exit(code=1)

    if name:
        folder = summary_root / name
        if not folder.exists():
            typer.echo(f"ERROR: meeting folder '{name}' not found", err=True)
            raise typer.Exit(code=1)
        def _date_key(f: Path) -> datetime:
            try:
                return datetime.strptime(f.stem, "%m-%d-%y")
            except ValueError:
                return datetime.min

        files = sorted(folder.glob("*.txt"), key=_date_key, reverse=True)
        transcript_dir = base / "t" / name
        print(f"Meeting: {name} ({len(files)} sessions)\n")
        print(f"{'SLUG':<22}  {'S':<3}  {'T':<3}  TITLE")
        print("─" * 70)
        for f in files:
            has_summary = f.stat().st_size > 0
            t_file = transcript_dir / f.name
            has_transcript = t_file.exists() and t_file.stat().st_size > 0
            slug = f"{name}/{f.stem}"
            s_mark = "✓" if has_summary else "–"
            t_mark = "✓" if has_transcript else "–"
            title = _extract_session_title(f) if has_summary else "n/a"
            print(f"{slug:<22}  {s_mark:<3}  {t_mark:<3}  {title[:45]}")
    else:
        folders = sorted(p.name for p in summary_root.iterdir() if p.is_dir())
        print(f"{'MEETING':<20}  {'SESSIONS':<10}  LATEST")
        print("─" * 50)
        for folder_name in folders:
            folder = summary_root / folder_name
            files = sorted(folder.glob("*.txt"))
            count = len(files)
            latest = files[-1].stem if files else "–"
            print(f"{folder_name:<20}  {count:<10}  {latest}")


@lekhak_app.command("show")
def lekhak_show(
    slug: Annotated[str, typer.Argument(help="Session slug (name/MM-DD-YY) or just name for latest")],
    transcript: Annotated[bool, typer.Option("--transcript", "-t", help="Show transcript instead of notes")] = False,
    base_dir: Annotated[str, typer.Option("--dir", help="Lekhak granola data dir")] = "",
) -> None:
    """Show contents of an exported meeting."""
    settings = get_settings()
    base = Path(base_dir) if base_dir else settings.lekhak_path
    subdir = "t" if transcript else "s"

    if "/" in slug:
        name, date_code = slug.rsplit("/", 1)
        target = base / subdir / name / f"{date_code}.txt"
    else:
        name = slug
        folder = base / subdir / name
        if not folder.exists():
            typer.echo(f"ERROR: meeting folder '{name}' not found", err=True)
            raise typer.Exit(code=1)
        files = sorted(folder.glob("*.txt"))
        if not files:
            typer.echo(f"ERROR: no files in {subdir}/{name}/", err=True)
            raise typer.Exit(code=1)
        target = files[-1]

    if not target.exists():
        typer.echo(f"ERROR: file not found: {target}", err=True)
        raise typer.Exit(code=1)

    date_label = _friendly_date(target.name)
    kind = "transcript" if transcript else "notes"
    folder = target.parent
    total = len(list(folder.glob("*.txt")))
    print(f"── {name} / {date_label} ({kind}, {total} sessions total) ──")
    if total > 1:
        print(f"   All sessions: granola-tool lekhak list {name}")
    print()
    print(target.read_text(encoding="utf-8"))


@lekhak_app.command("edit")
def lekhak_edit(
    slug: Annotated[str, typer.Argument(help="Session slug (name/MM-DD-YY) from 'lekhak list'")],
    transcript: Annotated[bool, typer.Option("--transcript", "-t", help="Edit transcript instead of notes")] = False,
    base_dir: Annotated[str, typer.Option("--dir", help="Lekhak granola data dir")] = "",
) -> None:
    """Open a meeting session in $EDITOR."""
    import os
    import subprocess

    settings = get_settings()
    base = Path(base_dir) if base_dir else settings.lekhak_path

    if "/" not in slug:
        typer.echo("ERROR: slug must be in format 'name/MM-DD-YY' (e.g. ai-proj/09-02-25)", err=True)
        raise typer.Exit(code=1)

    name, date_code = slug.rsplit("/", 1)
    subdir = "t" if transcript else "s"
    target = base / subdir / name / f"{date_code}.txt"

    if not target.exists():
        typer.echo(f"ERROR: file not found: {target}", err=True)
        raise typer.Exit(code=1)

    editor = os.environ.get("EDITOR", "vim")
    subprocess.run([editor, str(target)])


@lekhak_app.command("record")
def lekhak_record(
    meeting_id: Annotated[str, typer.Argument(help="Granola meeting ID (prefix) or title substring")],
    name: Annotated[str, typer.Argument(help="Meeting folder name (e.g. 'tactical')")],
    base_dir: Annotated[str, typer.Option("--dir", help="Lekhak granola data dir")] = "",
    create: Annotated[bool, typer.Option("--create", help="Create meeting folder if it doesn't exist")] = False,
    notes_only: Annotated[bool, typer.Option("--notes-only", help="Export only the AI-generated notes")] = False,
    transcript_only: Annotated[bool, typer.Option("--transcript-only", help="Export only the transcript")] = False,
) -> None:
    """Record a Granola meeting into the lekhak knowledge base."""
    settings = get_settings()
    base = Path(base_dir) if base_dir else settings.lekhak_path
    summary_dir = base / "s" / name
    transcript_dir = base / "t" / name

    if not summary_dir.exists() or not transcript_dir.exists():
        if create:
            summary_dir.mkdir(parents=True, exist_ok=True)
            transcript_dir.mkdir(parents=True, exist_ok=True)
        else:
            available = sorted(p.name for p in (base / "s").iterdir() if p.is_dir())
            typer.echo(f"ERROR: meeting folder '{name}' not found.", err=True)
            typer.echo(f"Available: {', '.join(available)}", err=True)
            typer.echo("Use --create to create a new folder.", err=True)
            raise typer.Exit(code=1)

    try:
        doc = require_document(meeting_id)
    except NotFoundError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(code=1) from None

    full = get_document(doc["id"])
    granola_uuid = _extract_uuid(full)
    title: str = full.get("title") or "(Untitled)"
    created_at: str = full.get("created_at", "")
    date_filename = _format_date_filename(created_at)
    date_header = _format_date_header(created_at)
    date_iso = created_at[:10]
    slug = f"{name}/{date_filename}"
    attendees = full.get("attendees", [])
    participant_names = [a.get("name", "") for a in attendees if a.get("name")]

    note_api_id = full.get("id", "n/a")
    frontmatter = _build_frontmatter(
        slug=slug, title=title, date=date_iso, participants=participant_names,
        granola_id=granola_uuid, note_id=note_api_id,
    )

    summary_file = summary_dir / f"{date_filename}.txt"
    transcript_file = transcript_dir / f"{date_filename}.txt"
    wrote_summary = False
    wrote_transcript = False

    if not transcript_only:
        notes_md = full.get("summary_markdown") or ""
        if notes_md:
            summary_file.write_text(frontmatter + notes_md, encoding="utf-8")
            wrote_summary = True

    if not notes_only:
        utterances: list[dict[str, Any]] = full.get("transcript", [])
        if utterances:
            people_for_transcript = [{"name": a.get("name", ""), "email": a.get("email", "")} for a in attendees]
            transcript_text = _build_transcript_text(title, date_header, people_for_transcript, utterances)
            transcript_file.write_text(frontmatter + transcript_text, encoding="utf-8")
            wrote_transcript = True

    print(
        json.dumps(
            {
                "meeting": title,
                "date": date_filename,
                "folder": name,
                "summary": str(summary_file) if wrote_summary else None,
                "transcript": str(transcript_file) if wrote_transcript else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@lekhak_app.command("enrich")
def lekhak_enrich(
    name: Annotated[str, typer.Argument(help="Meeting folder name to enrich with frontmatter")],
    base_dir: Annotated[str, typer.Option("--dir", help="Lekhak granola data dir")] = "",
) -> None:
    """Add frontmatter to existing files that lack it."""
    settings = get_settings()
    base = Path(base_dir) if base_dir else settings.lekhak_path
    summary_dir = base / "s" / name
    transcript_dir = base / "t" / name

    if not summary_dir.exists():
        typer.echo(f"ERROR: meeting folder '{name}' not found", err=True)
        raise typer.Exit(code=1)

    enriched = 0
    skipped = 0

    for summary_file in sorted(summary_dir.glob("*.txt")):
        content = summary_file.read_text(encoding="utf-8")
        if content.startswith("---\n"):
            skipped += 1
            continue

        date_code = summary_file.stem
        slug = f"{name}/{date_code}"
        transcript_file = transcript_dir / summary_file.name

        title = "n/a"
        participants: list[str] = []
        date_iso = "n/a"

        if transcript_file.exists():
            t_content = transcript_file.read_text(encoding="utf-8")
            t_lines = t_content.splitlines()
            for line in t_lines[:10]:
                if line.startswith("Meeting Title: "):
                    title = line.removeprefix("Meeting Title: ").strip()
                elif line.startswith("Meeting participants: "):
                    raw = line.removeprefix("Meeting participants: ").strip()
                    participants = [p.strip() for p in raw.split(",") if p.strip()]
                elif line.startswith("Date: "):
                    title_date = line.removeprefix("Date: ").strip()
                    date_iso = _parse_short_date(title_date, date_code)

        if title == "n/a":
            title = _extract_session_title(summary_file)

        if date_iso == "n/a":
            date_iso = _parse_short_date("", date_code)

        frontmatter = _build_frontmatter(
            slug=slug, title=title, date=date_iso, participants=participants
        )

        summary_file.write_text(frontmatter + content, encoding="utf-8")

        if transcript_file.exists():
            t_content = transcript_file.read_text(encoding="utf-8")
            if not t_content.startswith("---\n"):
                transcript_file.write_text(frontmatter + t_content, encoding="utf-8")

        enriched += 1

    print(f"Enriched {enriched} sessions, skipped {skipped} (already have frontmatter)")


def _parse_short_date(date_str: str, date_code: str) -> str:
    """Convert MM-DD-YY date code to ISO format."""
    try:
        dt = datetime.strptime(date_code, "%m-%d-%y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return "n/a"


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from file content. Returns (metadata dict, body)."""
    if not content.startswith("---\n"):
        return {}, content
    end_idx = content.index("---\n", 4) + 4
    fm_text = content[4 : end_idx - 4]
    body = content[end_idx:]
    metadata: dict[str, str] = {}
    for line in fm_text.splitlines():
        if ": " in line:
            key, val = line.split(": ", 1)
            metadata[key.strip()] = val.strip()
    return metadata, body


def _write_frontmatter_and_body(filepath: Path, metadata: dict[str, str], body: str) -> None:
    """Write file with updated frontmatter."""
    lines = ["---"]
    for key in ["slug", "granola_id", "title", "date", "participants"]:
        if key in metadata:
            lines.append(f"{key}: {metadata[key]}")
    lines.append("---")
    lines.append("")
    filepath.write_text("\n".join(lines) + body, encoding="utf-8")


@lekhak_app.command("reconcile")
def lekhak_reconcile(
    name: Annotated[str, typer.Argument(help="Meeting folder name to reconcile with Granola")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="How many Granola meetings to search")] = 100,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show matches without writing")] = False,
    base_dir: Annotated[str, typer.Option("--dir", help="Lekhak granola data dir")] = "",
) -> None:
    """Match lekhak sessions to Granola meetings and update frontmatter."""
    from granola_tool.documents import list_documents

    settings = get_settings()
    base = Path(base_dir) if base_dir else settings.lekhak_path
    summary_dir = base / "s" / name
    transcript_dir = base / "t" / name

    if not summary_dir.exists():
        typer.echo(f"ERROR: meeting folder '{name}' not found", err=True)
        raise typer.Exit(code=1)

    docs = list_documents(limit=limit)

    matched = 0
    unmatched = 0
    already_done = 0
    used_ids: set[str] = set()

    for summary_file in sorted(summary_dir.glob("*.txt")):
        date_code = summary_file.stem
        slug = f"{name}/{date_code}"
        date_iso = _parse_short_date("", date_code)

        content = summary_file.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(content)

        if metadata.get("granola_id", "n/a") != "n/a":
            used_ids.add(metadata["granola_id"])
            already_done += 1
            continue

        title_from_fm = metadata.get("title", "")

        available_docs = [d for d in docs if _extract_uuid(d) not in used_ids]
        match = _find_granola_match(available_docs, date_iso, title_from_fm, name)

        if match:
            doc_id = _extract_uuid(match)
            doc_title = match.get("title") or title_from_fm
            attendees = match.get("attendees", [])
            participant_names = [a.get("name", "") for a in attendees if a.get("name")]
            if not participant_names:
                owner = match.get("owner", {})
                if isinstance(owner, dict) and owner.get("name"):
                    participant_names = [owner["name"]]

            new_meta = {
                "slug": slug,
                "granola_id": doc_id,
                "title": doc_title,
                "date": date_iso,
                "participants": f"[{', '.join(participant_names)}]" if participant_names else "[n/a]",
            }

            used_ids.add(doc_id)
            if dry_run:
                print(f"  MATCH: {slug} → {doc_id[:8]} ({doc_title})")
            else:
                _write_frontmatter_and_body(summary_file, new_meta, body)
                t_file = transcript_dir / summary_file.name
                if t_file.exists():
                    t_content = t_file.read_text(encoding="utf-8")
                    _, t_body = _parse_frontmatter(t_content)
                    _write_frontmatter_and_body(t_file, new_meta, t_body)
                print(f"  UPDATED: {slug} → {doc_id[:8]} ({doc_title})")
            matched += 1
        else:
            if dry_run:
                print(f"  NO MATCH: {slug} (date={date_iso}, title={title_from_fm[:40]})")
            unmatched += 1

    print(f"\nReconciled: {matched} matched, {unmatched} unmatched, {already_done} already had ID")


def _find_granola_match(
    docs: list[dict[str, Any]], date_iso: str, title: str, folder_name: str
) -> dict[str, Any] | None:
    """Find best Granola match for a lekhak session by date and title similarity."""
    from datetime import timedelta

    try:
        target_date = datetime.strptime(date_iso, "%Y-%m-%d").date()
    except ValueError:
        return None

    # Collect candidates within ±3 days, scored by date proximity
    candidates: list[tuple[int, dict[str, Any]]] = []
    for doc in docs:
        doc_date_str = doc.get("created_at", "")[:10]
        try:
            doc_date = datetime.strptime(doc_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        diff = abs((doc_date - target_date).days)
        if diff <= 3:
            candidates.append((diff, doc))

    if not candidates:
        return None

    title_lower = title.lower()
    folder_lower = folder_name.lower()

    # Priority 1: title matches folder name (prefer exact date, then nearby)
    folder_matches = [(diff, doc) for diff, doc in candidates if folder_lower in (doc.get("title") or "").lower()]
    if folder_matches:
        folder_matches.sort(key=lambda x: x[0])
        return folder_matches[0][1]

    # Priority 2: stored title matches doc title
    if title_lower and title_lower != "n/a":
        title_matches = []
        for diff, doc in candidates:
            doc_title = (doc.get("title") or "").lower()
            if title_lower in doc_title or doc_title in title_lower:
                title_matches.append((diff, doc))
        if title_matches:
            title_matches.sort(key=lambda x: x[0])
            return title_matches[0][1]

    # Priority 3: folder name in attendee names
    people_matches = []
    for diff, doc in candidates:
        attendees = doc.get("attendees", [])
        if isinstance(attendees, list):
            for a in attendees:
                if isinstance(a, dict) and folder_lower in (a.get("name") or "").lower():
                    people_matches.append((diff, doc))
                    break
    if people_matches:
        people_matches.sort(key=lambda x: x[0])
        return people_matches[0][1]

    return None


@lekhak_app.command("sync")
def lekhak_sync(
    limit: Annotated[int, typer.Option("--limit", "-n", help="How many Granola meetings to check")] = 50,
    base_dir: Annotated[str, typer.Option("--dir", help="Lekhak granola data dir")] = "",
) -> None:
    """Show recent Granola meetings not yet in lekhak."""
    from granola_tool.documents import list_documents

    settings = get_settings()
    base = Path(base_dir) if base_dir else settings.lekhak_path

    known_ids: set[str] = set()
    known_dates_titles: set[tuple[str, str]] = set()
    for subdir in (base / "s").iterdir():
        if not subdir.is_dir():
            continue
        for f in subdir.glob("*.txt"):
            content = f.read_text(encoding="utf-8")
            metadata, _ = _parse_frontmatter(content)
            gid = metadata.get("granola_id", "")
            if gid and gid != "n/a":
                known_ids.add(gid)
            date = metadata.get("date", "")
            title = metadata.get("title", "").lower()
            if date and title:
                known_dates_titles.add((date, title))

    docs = list_documents(limit=limit)
    missing: list[dict[str, Any]] = []
    for doc in docs:
        uuid = _extract_uuid(doc)
        note_id = doc.get("id", "")
        doc_date = doc.get("created_at", "")[:10]
        doc_title = (doc.get("title") or "").lower()
        if uuid in known_ids or note_id in known_ids:
            continue
        if (doc_date, doc_title) in known_dates_titles:
            continue
        missing.append(doc)

    if not missing:
        print("All recent Granola meetings are already in lekhak.")
        return

    print(f"Found {len(missing)} Granola meetings not in lekhak:\n")
    print(f"{'ID':<8}  {'DATE':<12}  {'TITLE':<45}  ATTENDEES")
    print("─" * 90)
    for doc in missing:
        uuid = _extract_uuid(doc)[:8]
        title = (doc.get("title") or "(Untitled)")[:45]
        date = doc.get("created_at", "")[:10]
        attendees_list = doc.get("attendees", [])
        attendees = ", ".join(a.get("name", "") for a in attendees_list[:3])
        if len(attendees_list) > 3:
            attendees += f" +{len(attendees_list) - 3}"
        print(f"{uuid:<8}  {date:<12}  {title:<45}  {attendees}")

    print(f"\nTo record: granola-tool lekhak record <id> <folder-name> [--create]")
