from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from bson import ObjectId

from fur_mongo import db
from schemas.event_schema import EventModel

log = logging.getLogger(__name__)

COLLECTION_NAME = "calendar_events"
collection = db[COLLECTION_NAME]


async def create_event(
    event: EventModel,
    *,
    col=None,
) -> EventModel:
    """Insert a new event document into the collection.

    Args:
        event: The event to store in the database.
        col: Optional MongoDB collection. Defaults to the module level
            ``collection``.

    Returns:
        EventModel: The stored event with its ``id`` field populated.

    Raises:
        bson.errors.InvalidId: If the event contains an invalid ``_id`` field.
        pymongo.errors.PyMongoError: If the insert operation fails.
    """
    col = col if col is not None else collection
    if hasattr(event, "model_dump"):
        data = event.model_dump(by_alias=True)
    else:  # pragma: no cover - Pydantic < 2
        data = event.dict(by_alias=True)
    if data.get("_id") is None:
        data.pop("_id")
    result = await asyncio.to_thread(col.insert_one, data)
    event.id = result.inserted_id
    return event


async def get_event_by_id(
    event_id: str | ObjectId,
    *,
    col=None,
) -> Optional[EventModel]:
    """Return a single event by ObjectId.

    Args:
        event_id: The MongoDB ObjectId or its string representation.
        col: Optional MongoDB collection. Defaults to the module level
            ``collection``.

    Returns:
        Optional[EventModel]: The matching event or ``None`` if not found.

    Raises:
        bson.errors.InvalidId: If ``event_id`` cannot be converted to
            :class:`~bson.ObjectId`.
        pymongo.errors.PyMongoError: If the query fails.
    """
    col = col if col is not None else collection
    if not isinstance(event_id, ObjectId):
        event_id = ObjectId(event_id)
    doc = await asyncio.to_thread(col.find_one, {"_id": event_id})
    return EventModel(**doc) if doc else None


async def delete_event_by_id(
    event_id: str | ObjectId,
    *,
    col=None,
) -> int:
    """Delete an event by its ObjectId.

    Args:
        event_id: The MongoDB ObjectId or its string representation.
        col: Optional MongoDB collection. Defaults to the module level
            ``collection``.

    Returns:
        int: Number of deleted documents (``0`` or ``1``).

    Raises:
        bson.errors.InvalidId: If ``event_id`` cannot be converted to
            :class:`~bson.ObjectId`.
        pymongo.errors.PyMongoError: If the delete operation fails.
    """
    col = col if col is not None else collection
    if not isinstance(event_id, ObjectId):
        event_id = ObjectId(event_id)
    res = await asyncio.to_thread(col.delete_one, {"_id": event_id})
    return res.deleted_count


async def get_events_by_guild(
    guild_id: str,
    *,
    col=None,
) -> List[EventModel]:
    """Return all events for a Discord guild.

    Args:
        guild_id: Discord guild identifier whose events are requested.
        col: Optional MongoDB collection. Defaults to the module level
            ``collection``.

    Returns:
        List[EventModel]: List of matching events (may be empty).

    Raises:
        pymongo.errors.PyMongoError: If the query fails.
    """
    col = col if col is not None else collection
    docs = await asyncio.to_thread(lambda: list(col.find({"guild_id": guild_id})))
    return [EventModel(**d) for d in docs]


async def get_events_in_range(
    start: datetime,
    end: datetime,
    *,
    col=None,
) -> List[EventModel]:
    """Return events between ``start`` and ``end`` sorted by time.

    Args:
        start: Start of the time range (inclusive).
        end: End of the time range (exclusive).
        col: Optional MongoDB collection. Defaults to the module level
            ``collection``.

    Returns:
        List[EventModel]: Events occurring in the given time span.

    Raises:
        pymongo.errors.PyMongoError: If the query fails.
    """
    col = col if col is not None else collection
    docs = await asyncio.to_thread(
        lambda: list(col.find({"event_time": {"$gte": start, "$lt": end}}).sort("event_time", 1))
    )
    return [EventModel(**d) for d in docs]


async def upsert_event(
    data: dict,
    *,
    col=None,
) -> None:
    """Upsert an event document by ``google_id`` field.

    Args:
        data: Event fields to update or insert. Must contain ``google_id``.
        col: Optional MongoDB collection. Defaults to the module level
            ``collection``.

    Raises:
        KeyError: If ``data`` does not include ``google_id``.
        pymongo.errors.PyMongoError: If the upsert operation fails.
    """
    col = col if col is not None else collection
    if asyncio.iscoroutinefunction(col.update_one):
        await col.update_one({"google_id": data["google_id"]}, {"$set": data}, upsert=True)
    else:  # pragma: no cover - sync collections
        await asyncio.to_thread(
            col.update_one,
            {"google_id": data["google_id"]},
            {"$set": data},
            upsert=True,
        )
