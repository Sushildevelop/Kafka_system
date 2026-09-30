from dataclasses import dataclass
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import Settings
from app.models.event import Event
from app.models.study_group import GroupMessage, StudyGroup
@dataclass(slots=True)
class DatabaseConnections:
    write_client: AsyncIOMotorClient
    read_client: AsyncIOMotorClient
    write_database: AsyncIOMotorDatabase
    read_database: AsyncIOMotorDatabase
async def initialize_database(settings: Settings)->DatabaseConnections:
    wc=AsyncIOMotorClient(settings.database_write_url,serverSelectionTimeoutMS=5000,tz_aware=True); rc=AsyncIOMotorClient(settings.database_read_url,serverSelectionTimeoutMS=5000,tz_aware=True)
    wd=wc[settings.mongodb_database]; rd=rc[settings.mongodb_database]
    try: await wd.command("ping"); await init_beanie(database=wd,document_models=[Event,StudyGroup,GroupMessage])
    except Exception: wc.close(); rc.close(); raise
    return DatabaseConnections(wc,rc,wd,rd)
async def close_database(connections: DatabaseConnections)->None: connections.write_client.close(); connections.read_client.close()
