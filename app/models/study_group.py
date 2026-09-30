from datetime import datetime, timezone
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field


class StudyGroup(Document):
    """A study-only group conversation. There is intentionally no 1:1 chat model."""

    group_id: Annotated[str, Indexed(unique=True)]
    name: str = Field(min_length=1, max_length=120)
    owner_id: Annotated[str, Indexed()]
    member_ids: list[str] = Field(default_factory=list, min_length=1)
    created_at: Annotated[datetime, Indexed(index_type=-1)] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "study_groups"


class GroupMessage(Document):
    """Persisted group message. Binary media is stored outside Kafka."""

    message_id: Annotated[str, Indexed(unique=True)]
    group_id: Annotated[str, Indexed()]
    sender_id: Annotated[str, Indexed()]
    message_type: Annotated[str, Indexed()]
    text: str | None = None
    media_url: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    created_at: Annotated[datetime, Indexed(index_type=-1)] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "study_group_messages"
        indexes = [
            [("group_id", 1), ("created_at", -1)],
        ]
