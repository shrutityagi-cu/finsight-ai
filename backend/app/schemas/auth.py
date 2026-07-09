from __future__ import annotations

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema


class LoginRequest(BaseSchema):
    """Schema for login requests."""

    email_or_username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)


class RefreshTokenRequest(BaseSchema):
    """Schema for refresh-token requests."""

    refresh_token: str = Field(..., min_length=10)


class LogoutRequest(BaseSchema):
    """Schema for logout requests."""

    refresh_token: str | None = Field(default=None, min_length=10)


class TokenResponse(BaseSchema):
    """Schema for token responses."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthenticatedUserResponse(BaseSchema):
    """Schema for the authenticated user payload."""

    id: str
    email: EmailStr
    username: str
    full_name: str | None = None
