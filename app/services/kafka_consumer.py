import asyncio
import json

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from app.core.config import Settings
from app.repositories.event_repository import EventRepository
from app.schemas.event import EventMessage
from app.services.event_service import process_event
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KafkaConsumerService:
    def __init__(self, settings: Settings, event_repository: EventRepository) -> None:
        self._settings = settings
        self._event_repository = event_repository
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        consumer = AIOKafkaConsumer(
            self._settings.kafka_topic,
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            group_id=self._settings.kafka_consumer_group,
            auto_offset_reset=self._settings.kafka_auto_offset_reset,
            enable_auto_commit=False,
            request_timeout_ms=5000,
        )
        try:
            await consumer.start()
        except (KafkaError, OSError):
            logger.exception("Kafka consumer could not connect; consuming is unavailable")
            return

        self._consumer = consumer
        self._task = asyncio.create_task(self._consume(), name="kafka-event-consumer")
        logger.info("Kafka consumer started for topic %s", self._settings.kafka_topic)

    async def _consume(self) -> None:
        if self._consumer is None:
            return

        while True:
            try:
                message = await self._consumer.getone()
            except (KafkaError, OSError):
                logger.exception("Kafka consumer read failed; retrying")
                await asyncio.sleep(1)
                continue

            try:
                event_data = json.loads(message.value.decode("utf-8"))
                event = EventMessage.model_validate(event_data)
            except (ValueError, TypeError):
                logger.exception("Invalid event message; skipping offset %s", message.offset)
                await self._consumer.commit()
                continue

            logger.info("Event received from Kafka: %s", event.event_id)
            try:
                await process_event(event, self._event_repository)
                await self._consumer.commit()
            except Exception:
                logger.exception("Could not process event %s; retrying", event.event_id)
                self._consumer.seek(message.topic_partition, message.offset)
                await asyncio.sleep(1)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
            logger.info("Kafka consumer stopped")
