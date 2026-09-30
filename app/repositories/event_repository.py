from datetime import datetime, timezone

from beanie.operators import Set
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.event import Event
from app.schemas.event import EventMessage, EventResponse


class EventRepository:
    """The only component that selects a MongoDB read or write path."""

    def __init__(
        self,
        write_database: AsyncIOMotorDatabase,
        read_database: AsyncIOMotorDatabase,
    ) -> None:
        self._write_collection = write_database[Event.Settings.name]
        self._read_collection = read_database[Event.Settings.name]

    async def save_processed(self, event: EventMessage) -> None:
        """Idempotently persist one consumed Kafka event on the primary.

        ``$setOnInsert`` protects the original event body during Kafka redelivery,
        while ``$set`` completes an event that was previously only received.
        """
        processed_at = datetime.now(timezone.utc)
        await Event.find_one({"event_id": event.event_id}).upsert(
            Set(
                {
                    "status": "processed",
                    "processed_at": processed_at,
                }
            ),
            on_insert=Event(
                event_id=event.event_id,
                event_type=event.event_type,
                user_id=event.user_id,
                payload=event.payload,
                created_at=event.created_at,
                status="processed",
                processed_at=processed_at,
            ),
        )

    async def list_processed(
        self, skip: int, limit: int, *, use_primary: bool
    ) -> list[EventResponse]:
        collection = self._write_collection if use_primary else self._read_collection
        cursor = (
            collection.find({"status": "processed"}, {"_id": 0})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        documents = await cursor.to_list(length=limit)
        return [EventResponse.model_validate(document) for document in documents]
