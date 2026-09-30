from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.database import close_database, initialize_database
from app.repositories.event_repository import EventRepository
from app.services.kafka_consumer import KafkaConsumerService
from app.services.kafka_producer import KafkaProducerService
from app.services.kafka_admin import create_topics
from app.utils.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_connections = await initialize_database(settings)
    producer: KafkaProducerService | None = None
    consumer: KafkaConsumerService | None = None
    try:
        event_repository = EventRepository(
            database_connections.write_database, database_connections.read_database
        )
        producer = KafkaProducerService(settings)
        consumer = KafkaConsumerService(settings, event_repository)
        app.state.kafka_producer = producer
        app.state.event_repository = event_repository

        await create_topics(settings)
        await producer.start()
        await consumer.start()
        app.state.kafka_consumer = consumer
        logger.info("Application started")
        yield
    finally:
        if consumer is not None:
            await consumer.stop()
        if producer is not None:
            await producer.stop()
        await close_database(database_connections)
        logger.info("Application stopped")


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.include_router(health_router)
app.include_router(events_router, prefix="/api")
