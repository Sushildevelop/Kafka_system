from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.study_group import GroupMessage, StudyGroup
from app.schemas.study_group import GroupChatMessageEvent, GroupMessageResponse, StudyGroupResponse


class StudyGroupRepository:
    """Writes use the primary; chat history reads prefer a replica."""

    def __init__(self, write_database: AsyncIOMotorDatabase, read_database: AsyncIOMotorDatabase) -> None:
        self._write_groups = write_database[StudyGroup.Settings.name]
        self._read_groups = read_database[StudyGroup.Settings.name]
        self._write_messages = write_database[GroupMessage.Settings.name]
        self._read_messages = read_database[GroupMessage.Settings.name]

    async def create_group(self, group: StudyGroup) -> StudyGroupResponse:
        await group.insert()
        return StudyGroupResponse.model_validate(group)

    async def get_group(self, group_id: str, *, use_primary: bool = False) -> StudyGroup | None:
        collection = self._write_groups if use_primary else self._read_groups
        document = await collection.find_one({"group_id": group_id})
        return StudyGroup.model_validate(document) if document else None

    async def add_member(self, group_id: str, user_id: str) -> StudyGroup | None:
        result = await self._write_groups.find_one_and_update(
            {"group_id": group_id},
            {"$addToSet": {"member_ids": user_id}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            return_document=True,
        )
        return StudyGroup.model_validate(result) if result else None

    async def save_message(self, event: GroupChatMessageEvent) -> GroupMessageResponse:
        now = datetime.now(timezone.utc)
        await GroupMessage.find_one({"message_id": event.message_id}).upsert(
            {"$set": {"created_at": event.created_at}},
            on_insert=GroupMessage(
                message_id=event.message_id,
                group_id=event.group_id,
                sender_id=event.sender_id,
                message_type=event.message_type,
                text=event.text,
                media_url=event.media_url,
                file_name=event.file_name,
                mime_type=event.mime_type,
                file_size=event.file_size,
                created_at=event.created_at,
            ),
        )
        document = await self._write_messages.find_one({"message_id": event.message_id}, {"_id": 0})
        if not document:
            raise RuntimeError(f"Message {event.message_id} was not persisted")
        return GroupMessageResponse.model_validate(document)

    async def list_messages(self, group_id: str, skip: int, limit: int, *, use_primary: bool = False) -> list[GroupMessageResponse]:
        collection = self._write_messages if use_primary else self._read_messages
        cursor = collection.find({"group_id": group_id}, {"_id": 0}).sort("created_at", 1).skip(skip).limit(limit)
        return [GroupMessageResponse.model_validate(x) for x in await cursor.to_list(length=limit)]
