from dataclasses import dataclass

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import Settings
from app.models.event import Event
from app.models.study_group import GroupMessage, StudyGroup
from app.models.user import User


@dataclass(slots=True)
class DatabaseConnections:
    write_client: AsyncIOMotorClient
    read_client: AsyncIOMotorClient
    write_database: AsyncIOMotorDatabase
    read_database: AsyncIOMotorDatabase


async def initialize_database(settings: Settings) -> DatabaseConnections:
    write_client = AsyncIOMotorClient(
        settings.database_write_url,
        serverSelectionTimeoutMS=5000,
        tz_aware=True,
    )
    read_client = AsyncIOMotorClient(
        settings.database_read_url,
        serverSelectionTimeoutMS=5000,
        tz_aware=True,
    )
    write_database = write_client[settings.mongodb_database]
    read_database = read_client[settings.mongodb_database]

    try:
        await write_database.command("ping")
        await init_beanie(
            database=write_database,
            document_models=[Event, StudyGroup, GroupMessage, User],
        )
    except Exception:
        write_client.close()
        read_client.close()
        raise

    return DatabaseConnections(
        write_client,
        read_client,
        write_database,
        read_database,
    )


async def close_database(connections: DatabaseConnections) -> None:
    connections.write_client.close()
    connections.read_client.close()
