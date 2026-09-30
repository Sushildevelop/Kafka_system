from uuid import uuid4

from app.core.config import settings
from app.repositories.event_repository import EventRepository
from app.schemas.event import EventCreate, EventMessage, EventPublishedResponse
from app.services.kafka_producer import KafkaProducerService
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_event(
    event_data: EventCreate, producer: KafkaProducerService
) -> EventPublishedResponse:
    event = EventMessage(event_id=f"evt_{uuid4().hex}", **event_data.model_dump())
    await publish_event(producer, event)
    return EventPublishedResponse(
        success=True,
        message="Event published successfully",
        event_id=event.event_id,
    )


async def publish_event(producer: KafkaProducerService, event: EventMessage) -> None:
    await producer.send_event(
        settings.kafka_topic,
        event.event_id,
        event.model_dump(mode="json"),
    )


async def process_event(event: EventMessage, repository: EventRepository) -> None:
    await save_event(event, repository)
    logger.info("Event processed: %s", event.event_id)


async def save_event(event: EventMessage, repository: EventRepository) -> None:
    await repository.save_processed(event)
    logger.info("Event saved to MongoDB: %s", event.event_id)


async def list_events(
    repository: EventRepository,
    skip: int = 0,
    limit: int = 20,
    *,
    consistency: str = "eventual",
):
    """Read from a replica by default; strong reads explicitly use the primary."""
    return await repository.list_processed(
        skip=skip, limit=limit, use_primary=consistency == "strong"
    )
