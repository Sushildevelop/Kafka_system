from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any]


class EventMessage(EventCreate):
    event_id: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    event_type: str
    user_id: str
    payload: dict[str, Any]
    status: str
    created_at: datetime


class EventPublishedResponse(BaseModel):
    success: bool
    message: str
    event_id: str