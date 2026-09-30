from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect, status

from app.schemas.study_group import GroupMessageResponse, GroupTextMessageCreate, StudyGroupAddMember, StudyGroupCreate, StudyGroupResponse
from app.services.chat_manager import chat_connection_manager
from app.services.study_group_service import CHAT_TOPIC, create_group, process_chat_event, publish_text_message, require_member
from app.schemas.study_group import GroupChatMessageEvent
from app.services.kafka_producer import KafkaUnavailableError

router = APIRouter(prefix="/study-groups", tags=["study-groups"])

ALLOWED_MEDIA: dict[str, Literal["image", "file", "video"]] = {}
for prefix in ("image/",):
    ALLOWED_MEDIA[prefix] = "image"
for prefix in ("video/",):
    ALLOWED_MEDIA[prefix] = "video"


def media_type(content_type: str | None) -> Literal["image", "file", "video"]:
    if content_type and content_type.startswith("image/"):
        return "image"
    if content_type and content_type.startswith("video/"):
        return "video"
    return "file"


@router.post("", response_model=StudyGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_study_group(data: StudyGroupCreate, request: Request):
    return await create_group(data, request.app.state.study_group_repository)


@router.post("/{group_id}/members", response_model=StudyGroupResponse)
async def add_group_member(group_id: str, data: StudyGroupAddMember, request: Request):
    repository = request.app.state.study_group_repository
    group = await repository.add_member(group_id, data.user_id)
    if group is None:
        raise HTTPException(404, "Study group not found")
    return group


@router.get("/{group_id}/messages", response_model=list[GroupMessageResponse])
async def get_group_messages(group_id: str, request: Request, user_id: str = Query(...), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    repository = request.app.state.study_group_repository
    try:
        await require_member(group_id, user_id, repository)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    return await repository.list_messages(group_id, skip, limit)


@router.post("/{group_id}/messages/text", response_model=GroupChatMessageEvent, status_code=status.HTTP_202_ACCEPTED)
async def send_group_text(group_id: str, data: GroupTextMessageCreate, request: Request):
    try:
        return await publish_text_message(group_id, data, request.app.state.study_group_repository, request.app.state.kafka_producer)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except KafkaUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/{group_id}/messages/media", response_model=GroupChatMessageEvent, status_code=status.HTTP_202_ACCEPTED)
async def send_group_media(group_id: str, sender_id: str = Query(...), file: UploadFile = File(...), request: Request = None):
    repository = request.app.state.study_group_repository
    try:
        await require_member(group_id, sender_id, repository)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc

    content = await file.read()
    max_size = 50 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(413, "Media file exceeds the 50 MB limit")
    if not file.filename:
        raise HTTPException(400, "A file name is required")

    import os
    from pathlib import Path
    from uuid import uuid4

    message_id = f"msg_{uuid4().hex}"
    safe_name = os.path.basename(file.filename).replace(" ", "_")
    upload_dir = Path("uploads") / "study-groups" / group_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"{message_id}_{safe_name}"
    target.write_bytes(content)

    event = GroupChatMessageEvent(
        event_id=f"chat_evt_{uuid4().hex}", message_id=message_id, group_id=group_id,
        sender_id=sender_id, message_type=media_type(file.content_type),
        media_url=f"/media/study-groups/{group_id}/{target.name}", file_name=file.filename,
        mime_type=file.content_type, file_size=len(content),
    )
    try:
        await request.app.state.kafka_producer.send_event(CHAT_TOPIC, group_id, event.model_dump(mode="json"))
    except KafkaUnavailableError as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(503, str(exc)) from exc
    return event


@router.websocket("/{group_id}/ws")
async def group_chat_websocket(websocket: WebSocket, group_id: str, user_id: str = Query(...)):
    repository = websocket.app.state.study_group_repository
    try:
        await require_member(group_id, user_id, repository)
    except LookupError:
        await websocket.close(code=4404)
        return
    except PermissionError:
        await websocket.close(code=4403)
        return

    await chat_connection_manager.connect(group_id, websocket)
    try:
        while True:
            # Sending happens through HTTP -> Kafka -> consumer -> WebSocket broadcast.
            # This socket is intentionally receive-idle and group-only.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await chat_connection_manager.disconnect(group_id, websocket)
    except Exception:
        await chat_connection_manager.disconnect(group_id, websocket)
