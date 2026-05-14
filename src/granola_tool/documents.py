"""Document fetching layer — official Granola public API."""

from typing import Any

from granola_tool.api import api_request
from granola_tool.errors import NotFoundError


def list_documents(limit: int = 30, created_after: str = "") -> list[dict[str, Any]]:
    """Fetch notes from Granola API, paginating to reach the requested limit."""
    all_notes: list[dict[str, Any]] = []
    cursor = ""
    page_size = min(limit, 30)

    while len(all_notes) < limit:
        params: dict[str, str] = {"page_size": str(page_size)}
        if cursor:
            params["cursor"] = cursor
        if created_after:
            params["created_after"] = created_after

        result = api_request("/v1/notes", params)
        notes: list[dict[str, Any]] = result.get("notes", [])
        all_notes.extend(notes)

        if not result.get("hasMore", False) or not notes:
            break
        cursor = result.get("cursor", "")

    return all_notes[:limit]


def get_document(note_id: str) -> dict[str, Any]:
    """Fetch a single note with transcript."""
    result: dict[str, Any] = api_request(f"/v1/notes/{note_id}", {"include": "transcript"})
    if "code" in result and result.get("code") == "VALIDATION_ERROR":
        raise NotFoundError(f"Note not found: {note_id}")
    return result


def _extract_uuid(doc: dict[str, Any]) -> str:
    """Extract the original UUID from web_url for cross-referencing."""
    url = doc.get("web_url", "")
    if "/d/" in url:
        return url.split("/d/")[-1]
    return doc.get("id", "")


def find_document(docs: list[dict[str, Any]], meeting_id: str) -> dict[str, Any] | None:
    """Search docs list by note ID prefix (with/without not_), UUID prefix, or title substring."""
    for doc in docs:
        note_id: str = doc.get("id", "")
        note_id_short = note_id.removeprefix("not_")
        uuid = _extract_uuid(doc)
        title: str = doc.get("title") or ""
        if note_id.startswith(meeting_id) or note_id_short.startswith(meeting_id):
            return doc
        if uuid.startswith(meeting_id):
            return doc
        if meeting_id.lower() in title.lower():
            return doc
    return None


def require_document(meeting_id: str, limit: int = 100) -> dict[str, Any]:
    """Fetch documents and find one by ID/title, or raise NotFoundError."""
    docs = list_documents(limit=limit)
    doc = find_document(docs, meeting_id)
    if not doc:
        raise NotFoundError(f"Meeting not found: {meeting_id}")
    return doc
