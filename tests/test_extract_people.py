"""Tests for people extraction."""

from granola_tool.people import extract_people


def test_extract_people_returns_names_and_emails_from_nested_attendees():
    doc = {
        "people": {
            "attendees": [
                {
                    "details": {"person": {"name": {"fullName": "Alice Johnson"}}},
                    "email": "alice@example.com",
                },
                {
                    "details": {"person": {"name": {"fullName": "Bob Smith"}}},
                    "email": "bob@example.com",
                },
            ]
        }
    }

    result = extract_people(doc)

    assert result == [
        {"name": "Alice Johnson", "email": "alice@example.com"},
        {"name": "Bob Smith", "email": "bob@example.com"},
    ]
