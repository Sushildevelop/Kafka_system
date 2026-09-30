from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from beanie import Document, Indexed
from pydantic import Field


class Event(Document):
    event_id: Annotated[str, Indexed(unique=True)]
    event_type: Annotated[str, Indexed()]
    user_id: Annotated[str, Indexed()]
    payload: dict[str, Any]
    created_at: Annotated[
        datetime, Indexed(index_type=-1)
    ] = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: datetime | None = None
    status: Literal["received", "processed"] = "received"

    class Settings:
        name = "events"
