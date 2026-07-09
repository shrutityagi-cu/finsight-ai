from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.database.session import get_db
from app.models import User
from app.schemas.auth import (
    AuthenticatedUserResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Register a new user and issue access and refresh tokens."""
    return await AuthService.register_user(db, user_in)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_in: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate a user and issue access and refresh tokens."""
    return await AuthService.login_user(db, login_in)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_in: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Rotate refresh tokens and issue a new access and refresh token pair."""
    return await AuthService.refresh_access_token(db, refresh_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(
    logout_in: LogoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Revoke the current refresh token for the authenticated user."""
    await AuthService.logout_user(db, current_user, logout_in.refresh_token)


@router.get("/me", response_model=AuthenticatedUserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> AuthenticatedUserResponse:
    """Return the authenticated user profile."""
    return await AuthService.get_current_user_profile(current_user)
