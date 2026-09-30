from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


MessageType = Literal["text", "image", "file", "video"]


class StudyGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    owner_id: str = Field(min_length=1, max_length=100)
    member_ids: list[str] = Field(default_factory=list, max_length=500)


class StudyGroupAddMember(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)


class StudyGroupResponse(BaseModel):
    group_id: str
    name: str
    owner_id: str
    member_ids: list[str]
    created_at: datetime
    updated_at: datetime


class GroupTextMessageCreate(BaseModel):
    sender_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=10000)


class GroupMessageResponse(BaseModel):
    message_id: str
    group_id: str
    sender_id: str
    message_type: MessageType
    text: str | None = None
    media_url: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    created_at: datetime


class GroupChatMessageEvent(BaseModel):
    event_id: str
    message_id: str
    group_id: str
    sender_id: str
    message_type: MessageType
    text: str | None = None
    media_url: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_content(self):
        if self.message_type == "text" and not self.text:
            raise ValueError("text messages require text")
        if self.message_type != "text" and not self.media_url:
            raise ValueError("media messages require media_url")
        return self
