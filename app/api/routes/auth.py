from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies.auth import require_current_user_id
from app.schemas.user import AuthResponse, DeleteAccountResponse, GoogleLoginRequest
from app.services.auth_service import (
    AuthenticationError,
    delete_account,
    login_with_google,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/google", response_model=AuthResponse)
async def google_login(
    data: GoogleLoginRequest,
    request: Request,
) -> AuthResponse:
    try:
        return await login_with_google(
            data.credential,
            request.app.state.user_repository,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.delete("/account", response_model=DeleteAccountResponse)
async def delete_my_account(
    request: Request,
    user_id: str = Depends(require_current_user_id),
) -> DeleteAccountResponse:
    return await delete_account(
        user_id,
        request.app.state.user_repository,
    )
