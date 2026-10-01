from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings
from app.repositories.user_repository import UserRepository
from app.schemas.user import AuthResponse, DeleteAccountResponse, UserResponse


class AuthenticationError(ValueError):
    pass


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.auth_session_secret, salt="kafka-system-auth")


def _issue_session_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.auth_session_expire_minutes
    )
    return _serializer().dumps({"user_id": user_id, "exp": int(expires_at.timestamp())})


def get_user_id_from_session(token: str) -> str:
    try:
        payload = _serializer().loads(
            token, max_age=settings.auth_session_expire_minutes * 60
        )
    except (BadSignature, SignatureExpired) as exc:
        raise AuthenticationError("Invalid or expired authentication token") from exc

    user_id = payload.get("user_id")
    if not isinstance(user_id, str) or not user_id:
        raise AuthenticationError("Invalid authentication token")
    return user_id


async def login_with_google(
    credential: str, repository: UserRepository
) -> AuthResponse:
    try:
        info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.google_audiences,
        )
    except ValueError as exc:
        raise AuthenticationError("Invalid Google credential") from exc

    issuer = info.get("iss")
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        raise AuthenticationError("Invalid Google token issuer")

    google_sub = info.get("sub")
    email = info.get("email")
    if not google_sub or not email:
        raise AuthenticationError("Google credential does not contain required user claims")

    user = await repository.upsert_google_user(
        user_id=f"user_{uuid4().hex}",
        google_sub=str(google_sub),
        email=str(email),
        name=str(info.get("name") or email),
        picture=info.get("picture"),
        email_verified=bool(info.get("email_verified", False)),
    )
    return AuthResponse(
        success=True,
        message="Google login successful",
        access_token=_issue_session_token(user.user_id),
        user=UserResponse.model_validate(user),
    )


async def delete_account(
    user_id: str, repository: UserRepository
) -> DeleteAccountResponse:
    deleted = await repository.delete_by_user_id(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found",
        )
    return DeleteAccountResponse(
        success=True,
        message="User account deleted successfully",
    )
