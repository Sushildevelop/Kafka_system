from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.auth import router as auth_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.study_groups import router as study_groups_router
from app.core.config import settings
from app.core.database import close_database, initialize_database
from app.repositories.event_repository import EventRepository
from app.repositories.study_group_repository import StudyGroupRepository
from app.repositories.user_repository import UserRepository
from app.services.chat_kafka_consumer import StudyGroupChatConsumer
from app.services.chat_manager import chat_connection_manager
from app.services.kafka_admin import create_topics
from app.services.kafka_consumer import KafkaConsumerService
from app.services.kafka_producer import KafkaProducerService


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await initialize_database(settings)
    producer = consumer = chat_consumer = None

    try:
        event_repository = EventRepository(db.write_database, db.read_database)
        study_group_repository = StudyGroupRepository(
            db.write_database, db.read_database
        )
        user_repository = UserRepository(db.write_database, db.read_database)

        producer = KafkaProducerService(settings)
        consumer = KafkaConsumerService(settings, event_repository)
        chat_consumer = StudyGroupChatConsumer(
            settings, study_group_repository, chat_connection_manager
        )

        app.state.kafka_producer = producer
        app.state.event_repository = event_repository
        app.state.study_group_repository = study_group_repository
        app.state.user_repository = user_repository
        app.state.settings = settings

        await create_topics(settings)
        await producer.start()
        await consumer.start()
        await chat_consumer.start()

        yield
    finally:
        if chat_consumer:
            await chat_consumer.stop()
        if consumer:
            await consumer.stop()
        if producer:
            await producer.stop()
        await close_database(db)


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path("uploads/study-groups").mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory="uploads"), name="media")

app.include_router(health_router)
app.include_router(auth_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(study_groups_router, prefix="/api")
