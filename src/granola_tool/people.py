"""People and attendee extraction from Granola documents."""

from typing import Any


def extract_people(doc: dict[str, Any]) -> list[dict[str, str]]:
    """Extract attendee names/emails from document."""
    people = doc.get("people", {})
    if not isinstance(people, dict):
        return []
    attendees = people.get("attendees", [])
    result: list[dict[str, str]] = []
    for a in attendees:
        if isinstance(a, dict):
            name: str | None = None
            details = a.get("details", {})
            if isinstance(details, dict):
                person = details.get("person", {})
                if isinstance(person, dict):
                    name_obj = person.get("name", {})
                    if isinstance(name_obj, dict):
                        name = name_obj.get("fullName")
            email: str = a.get("email", "")
            result.append({"name": name or email.split("@", maxsplit=1)[0], "email": email})
    return result


def extract_calendar_times(doc: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract start/end times from calendar event."""
    cal = doc.get("google_calendar_event")
    if not cal or not isinstance(cal, dict):
        return None, None
    start: str | None = cal.get("start", {}).get("dateTime")
    end: str | None = cal.get("end", {}).get("dateTime")
    return start, end
