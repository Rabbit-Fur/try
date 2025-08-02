import logging
from datetime import datetime, timezone
from unittest.mock import ANY, MagicMock

import pytest

import google_calendar_sync as mod


def test_parse_datetime_valid_datetime():
    dt = mod._parse_datetime({"dateTime": "2024-05-10T12:30:00Z"})
    assert dt == datetime(2024, 5, 10, 12, 30, tzinfo=timezone.utc)


def test_parse_datetime_valid_date():
    dt = mod._parse_datetime({"date": "2024-05-10"})
    assert dt == datetime(2024, 5, 10, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("info", [None, {}, {"dateTime": "invalid"}])
def test_parse_datetime_invalid(info, caplog):
    with caplog.at_level(logging.WARNING):
        assert mod._parse_datetime(info) is None


def test_fetch_upcoming_events(monkeypatch):
    service = MagicMock()
    events = [{"id": "1"}, {"id": "2"}]
    service.events.return_value.list.return_value.execute.return_value = {"items": events}

    result = mod.fetch_upcoming_events(service=service, calendar_id="cal")

    assert result == events
    service.events.return_value.list.assert_called_once_with(
        calendarId="cal", singleEvents=True, orderBy="startTime", maxResults=2500
    )


def test_fetch_upcoming_events_missing_credentials(monkeypatch):
    monkeypatch.setattr(mod, "get_calendar_service", lambda: None)
    assert mod.fetch_upcoming_events(service=None, calendar_id="cal") == []


def test_fetch_upcoming_events_missing_calendar_id(monkeypatch):
    service = MagicMock()
    monkeypatch.setattr(mod.Config, "GOOGLE_CALENDAR_ID", None)
    assert mod.fetch_upcoming_events(service=service, calendar_id=None) == []


def test_sync_to_mongodb(monkeypatch):
    service = object()
    event = {
        "id": "g1",
        "summary": "Title",
        "start": {"dateTime": "2025-01-01T10:00:00Z"},
        "end": {"dateTime": "2025-01-01T11:00:00Z"},
        "updated": "2025-01-01T09:00:00Z",
    }
    monkeypatch.setattr(mod, "get_calendar_service", lambda: service)
    monkeypatch.setattr(mod, "fetch_upcoming_events", lambda service, calendar_id: [event])
    collection = MagicMock()
    monkeypatch.setattr(mod, "get_collection", lambda name: collection)

    count = mod.sync_to_mongodb(collection="events")

    assert count == 1
    collection.update_one.assert_called_once_with({"google_id": "g1"}, ANY, upsert=True)


def test_sync_to_mongodb_no_service(monkeypatch):
    monkeypatch.setattr(mod, "get_calendar_service", lambda: None)
    assert mod.sync_to_mongodb(collection="events") == 0
