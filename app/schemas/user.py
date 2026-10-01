from datetime import datetime

from pydantic import BaseModel, Field


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=1)


class UserResponse(BaseModel):
    user_id: str
    google_sub: str
    email: str
    name: str
    picture: str | None = None
    email_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class AuthResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class DeleteAccountResponse(BaseModel):
    success: bool
    message: str
