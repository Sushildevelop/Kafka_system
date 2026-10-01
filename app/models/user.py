from datetime import datetime, timezone
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field


class User(Document):
    """Application user authenticated exclusively through Google."""

    user_id: Annotated[str, Indexed(unique=True)]
    google_sub: Annotated[str, Indexed(unique=True)]
    email: Annotated[str, Indexed()]
    name: str
    picture: str | None = None
    email_verified: bool = False
    is_active: bool = True
    created_at: Annotated[datetime, Indexed(index_type=-1)] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: datetime | None = None

    class Settings:
        name = "users"
