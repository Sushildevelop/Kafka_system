from dataclasses import dataclass

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import Settings
from app.models.event import Event
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class DatabaseConnections:
    """Separate database handles for commands that write and commands that read."""

    write_client: AsyncIOMotorClient
    read_client: AsyncIOMotorClient
    write_database: AsyncIOMotorDatabase
    read_database: AsyncIOMotorDatabase


async def initialize_database(settings: Settings) -> DatabaseConnections:
    """Connect write operations to the primary and reads to replica members.

    MongoDB replication copies one logical database between replica-set members.
    Both clients therefore use ``settings.mongodb_database``; their routes differ
    through write concern and read preference, not through different collections.
    """
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
        await init_beanie(database=write_database, document_models=[Event])
    except Exception:
        write_client.close()
        read_client.close()
        logger.exception("Could not initialize MongoDB read/write connections")
        raise

    logger.info(
        "MongoDB initialized: writes=primary, reads=%s, database=%s",
        settings.mongodb_read_preference,
        settings.mongodb_database,
    )
    return DatabaseConnections(
        write_client=write_client,
        read_client=read_client,
        write_database=write_database,
        read_database=read_database,
    )


async def close_database(connections: DatabaseConnections) -> None:
    connections.write_client.close()
    connections.read_client.close()
    logger.info("MongoDB read/write connections closed")
