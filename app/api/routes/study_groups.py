from typing import Literal
from pathlib import Path
import os
from uuid import uuid4
from fastapi import APIRouter,File,HTTPException,Query,Request,UploadFile,WebSocket,WebSocketDisconnect,status
from app.schemas.study_group import GroupChatMessageEvent,GroupMessageResponse,GroupTextMessageCreate,StudyGroupAddMember,StudyGroupCreate,StudyGroupResponse,StudyGroupUpdate
from app.services.chat_manager import chat_connection_manager
from app.services.study_group_service import CHAT_TOPIC,create_group,publish_text_message,require_member
from app.services.kafka_producer import KafkaUnavailableError
router=APIRouter(prefix="/study-groups",tags=["study-groups"])
def media_type(content_type:str|None)->Literal["image","file","video"]:
    if content_type and content_type.startswith("image/"): return "image"
    if content_type and content_type.startswith("video/"): return "video"
    return "file"
@router.get("",response_model=list[StudyGroupResponse])
async def list_study_groups(request:Request,user_id:str=Query(...)):
    return await request.app.state.study_group_repository.list_groups_for_user(user_id)
@router.get("/{group_id}",response_model=StudyGroupResponse)
async def get_study_group(group_id:str,request:Request,user_id:str=Query(...)):
    try: return await require_member(group_id,user_id,request.app.state.study_group_repository)
    except LookupError as e: raise HTTPException(404,str(e)) from e
    except PermissionError as e: raise HTTPException(403,str(e)) from e
@router.post("",response_model=StudyGroupResponse,status_code=status.HTTP_201_CREATED)
async def create_study_group(data:StudyGroupCreate,request:Request): return await create_group(data,request.app.state.study_group_repository)
@router.patch("/{group_id}",response_model=StudyGroupResponse)
async def update_study_group(group_id:str,data:StudyGroupUpdate,request:Request,user_id:str=Query(...)):
    try:
        group=await require_member(group_id,user_id,request.app.state.study_group_repository)
    except LookupError as e: raise HTTPException(404,str(e)) from e
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    if group.owner_id != user_id: raise HTTPException(403,"Only the group owner can update this study group")
    updated=await request.app.state.study_group_repository.update_group(group_id,data.name)
    if updated is None: raise HTTPException(404,"Study group not found")
    return updated

@router.delete("/{group_id}",status_code=status.HTTP_204_NO_CONTENT)
async def delete_study_group(group_id:str,request:Request,user_id:str=Query(...)):
    try:
        group=await require_member(group_id,user_id,request.app.state.study_group_repository)
    except LookupError as e: raise HTTPException(404,str(e)) from e
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    if group.owner_id != user_id: raise HTTPException(403,"Only the group owner can delete this study group")
    if not await request.app.state.study_group_repository.delete_group(group_id): raise HTTPException(404,"Study group not found")

@router.delete("/{group_id}/members/{member_id}",response_model=StudyGroupResponse)
async def remove_group_member(group_id:str,member_id:str,request:Request,user_id:str=Query(...)):
    try:
        group=await require_member(group_id,user_id,request.app.state.study_group_repository)
    except LookupError as e: raise HTTPException(404,str(e)) from e
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    if user_id != group.owner_id and user_id != member_id: raise HTTPException(403,"Only the owner can remove another member")
    if member_id == group.owner_id: raise HTTPException(400,"The group owner cannot be removed")
    updated=await request.app.state.study_group_repository.remove_member(group_id,member_id)
    if updated is None: raise HTTPException(404,"Study group not found")
    return updated

@router.post("/{group_id}/members",response_model=StudyGroupResponse)
async def add_group_member(group_id:str,data:StudyGroupAddMember,request:Request):
    group=await request.app.state.study_group_repository.add_member(group_id,data.user_id)
    if group is None: raise HTTPException(404,"Study group not found")
    return group
@router.get("/{group_id}/messages",response_model=list[GroupMessageResponse])
async def get_group_messages(group_id:str,request:Request,user_id:str=Query(...),skip:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    try: await require_member(group_id,user_id,request.app.state.study_group_repository)
    except LookupError as e: raise HTTPException(404,str(e)) from e
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    return await request.app.state.study_group_repository.list_messages(group_id,skip,limit)
@router.post("/{group_id}/messages/text",response_model=GroupChatMessageEvent,status_code=status.HTTP_202_ACCEPTED)
async def send_group_text(group_id:str,data:GroupTextMessageCreate,request:Request):
    try: return await publish_text_message(group_id,data,request.app.state.study_group_repository,request.app.state.kafka_producer)
    except LookupError as e: raise HTTPException(404,str(e)) from e
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except KafkaUnavailableError as e: raise HTTPException(503,str(e)) from e
@router.post("/{group_id}/messages/media",response_model=GroupChatMessageEvent,status_code=status.HTTP_202_ACCEPTED)
async def send_group_media(group_id:str,request:Request,sender_id:str=Query(...),file:UploadFile=File(...)):
    try: await require_member(group_id,sender_id,request.app.state.study_group_repository)
    except LookupError as e: raise HTTPException(404,str(e)) from e
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    if not file.filename: raise HTTPException(400,"A file name is required")
    content=await file.read(); max_size=request.app.state.settings.chat_media_max_size_mb*1024*1024 if hasattr(request.app.state,"settings") else 50*1024*1024
    if len(content)>max_size: raise HTTPException(413,f"Media file exceeds the {max_size//(1024*1024)} MB limit")
    safe_name=os.path.basename(file.filename).replace(" ","_"); message_id=f"msg_{uuid4().hex}"; directory=Path("uploads")/"study-groups"/group_id; directory.mkdir(parents=True,exist_ok=True); target=directory/f"{message_id}_{safe_name}"; target.write_bytes(content)
    event=GroupChatMessageEvent(event_id=f"chat_evt_{uuid4().hex}",message_id=message_id,group_id=group_id,sender_id=sender_id,message_type=media_type(file.content_type),media_url=f"/media/study-groups/{group_id}/{target.name}",file_name=file.filename,mime_type=file.content_type,file_size=len(content))
    try: await request.app.state.kafka_producer.send_event(CHAT_TOPIC,group_id,event.model_dump(mode="json"))
    except KafkaUnavailableError as e: target.unlink(missing_ok=True); raise HTTPException(503,str(e)) from e
    return event
@router.websocket("/{group_id}/ws")
async def group_chat_websocket(websocket:WebSocket,group_id:str,user_id:str=Query(...)):
    try: await require_member(group_id,user_id,websocket.app.state.study_group_repository)
    except LookupError: await websocket.close(code=4404); return
    except PermissionError: await websocket.close(code=4403); return
    await chat_connection_manager.connect(group_id,websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: await chat_connection_manager.disconnect(group_id,websocket)
    except Exception: await chat_connection_manager.disconnect(group_id,websocket)
