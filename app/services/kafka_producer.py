import json
from typing import Any

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.core.config import Settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KafkaUnavailableError(RuntimeError):
    pass


class KafkaProducerService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            key_serializer=lambda key: key.encode("utf-8"),
            request_timeout_ms=5000,
        )
        try:
            await producer.start()
        except (KafkaError, OSError):
            logger.exception("Kafka producer could not connect; publishing is unavailable")
            return

        self._producer = producer
        logger.info("Kafka producer started")

    async def send_event(
        self, topic: str, event_id: str, event_data: dict[str, Any]
    ) -> None:
        if self._producer is None:
            raise KafkaUnavailableError("Kafka is unavailable; event was not published")
        try:
            await self._producer.send_and_wait(topic, event_data, key=event_id)
        except (KafkaError, OSError) as exc:
            logger.exception("Could not publish event %s", event_id)
            raise KafkaUnavailableError("Kafka could not accept the event") from exc

        logger.info("Event published to Kafka: %s", event_id)

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("Kafka producer stopped")