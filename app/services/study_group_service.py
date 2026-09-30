from uuid import uuid4

from app.core.config import settings
from app.repositories.study_group_repository import StudyGroupRepository
from app.schemas.study_group import GroupChatMessageEvent, GroupTextMessageCreate, StudyGroupCreate
from app.services.chat_manager import GroupChatConnectionManager
from app.services.kafka_producer import KafkaProducerService
from app.models.study_group import StudyGroup


CHAT_TOPIC = "study-group-chat"


async def create_group(data: StudyGroupCreate, repository: StudyGroupRepository):
    members = list(dict.fromkeys([data.owner_id, *data.member_ids]))
    group = StudyGroup(group_id=f"grp_{uuid4().hex}", name=data.name, owner_id=data.owner_id, member_ids=members)
    return await repository.create_group(group)


async def publish_text_message(group_id: str, data: GroupTextMessageCreate, repository: StudyGroupRepository, producer: KafkaProducerService):
    await require_member(group_id, data.sender_id, repository)
    event = GroupChatMessageEvent(
        event_id=f"chat_evt_{uuid4().hex}", message_id=f"msg_{uuid4().hex}", group_id=group_id,
        sender_id=data.sender_id, message_type="text", text=data.text,
    )
    await producer.send_event(CHAT_TOPIC, group_id, event.model_dump(mode="json"))
    return event


async def require_member(group_id: str, user_id: str, repository: StudyGroupRepository):
    group = await repository.get_group(group_id, use_primary=True)
    if group is None:
        raise LookupError("Study group not found")
    if user_id not in group.member_ids:
        raise PermissionError("User is not a member of this study group")
    return group


async def process_chat_event(event: GroupChatMessageEvent, repository: StudyGroupRepository, manager: GroupChatConnectionManager):
    message = await repository.save_message(event)
    await manager.broadcast(event.group_id, message.model_dump(mode="json"))
    return message
