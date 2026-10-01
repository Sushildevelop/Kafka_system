from datetime import datetime, timezone
from beanie.operators import Set
from motor.motor_asyncio import AsyncIOMotorDatabase\nfrom pymongo import ReturnDocument
from app.models.study_group import GroupMessage, StudyGroup
from app.schemas.study_group import GroupChatMessageEvent, GroupMessageResponse, StudyGroupResponse
class StudyGroupRepository:
    def __init__(self,write_database:AsyncIOMotorDatabase,read_database:AsyncIOMotorDatabase)->None:
        self._write_groups=write_database[StudyGroup.Settings.name]; self._read_groups=read_database[StudyGroup.Settings.name]
        self._write_messages=write_database[GroupMessage.Settings.name]; self._read_messages=read_database[GroupMessage.Settings.name]
    async def create_group(self,group:StudyGroup)->StudyGroupResponse: await group.insert(); return StudyGroupResponse.model_validate(group)
    async def list_groups_for_user(self,user_id:str,*,use_primary:bool=False)->list[StudyGroupResponse]:
        c=self._write_groups if use_primary else self._read_groups
        docs=await c.find({"member_ids":user_id},{"_id":0}).sort("updated_at",-1).to_list(length=100)
        return [StudyGroupResponse.model_validate(x) for x in docs]

    async def get_group(self,group_id:str,*,use_primary:bool=False)->StudyGroup|None:
        c=self._write_groups if use_primary else self._read_groups; d=await c.find_one({"group_id":group_id}); return StudyGroup.model_validate(d) if d else None
    async def update_group(self,group_id:str,name:str)->StudyGroupResponse|None:
        d=await self._write_groups.find_one_and_update({"group_id":group_id},{"$set":{"name":name,"updated_at":datetime.now(timezone.utc)}},return_document=ReturnDocument.AFTER)
        return StudyGroupResponse.model_validate(d) if d else None

    async def delete_group(self,group_id:str)->bool:
        result=await self._write_groups.delete_one({"group_id":group_id})
        return result.deleted_count == 1

    async def remove_member(self,group_id:str,user_id:str)->StudyGroup|None:
        d=await self._write_groups.find_one_and_update({"group_id":group_id},{"$pull":{"member_ids":user_id},"$set":{"updated_at":datetime.now(timezone.utc)}},return_document=ReturnDocument.AFTER)
        return StudyGroup.model_validate(d) if d else None

    async def add_member(self,group_id:str,user_id:str)->StudyGroup|None:
        d=await self._write_groups.find_one_and_update({"group_id":group_id},{"$addToSet":{"member_ids":user_id},"$set":{"updated_at":datetime.now(timezone.utc)}},return_document=ReturnDocument.AFTER); return StudyGroup.model_validate(d) if d else None
    async def save_message(self,event:GroupChatMessageEvent)->GroupMessageResponse:
        await GroupMessage.find_one({"message_id":event.message_id}).upsert(Set({"created_at":event.created_at}),on_insert=GroupMessage(message_id=event.message_id,group_id=event.group_id,sender_id=event.sender_id,message_type=event.message_type,text=event.text,media_url=event.media_url,file_name=event.file_name,mime_type=event.mime_type,file_size=event.file_size,created_at=event.created_at))
        d=await self._write_messages.find_one({"message_id":event.message_id},{"_id":0})
        if not d: raise RuntimeError(f"Message {event.message_id} was not persisted")
        return GroupMessageResponse.model_validate(d)
    async def list_messages(self,group_id:str,skip:int,limit:int,*,use_primary:bool=False)->list[GroupMessageResponse]:
        c=self._write_messages if use_primary else self._read_messages; cur=c.find({"group_id":group_id},{"_id":0}).sort("created_at",1).skip(skip).limit(limit); return [GroupMessageResponse.model_validate(x) for x in await cur.to_list(length=limit)]
