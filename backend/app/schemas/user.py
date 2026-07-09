from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict, EmailStr, Field

from app.schemas.base import BaseSchema


class UserCreate(BaseSchema):
    """Schema for creating a new user."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=255)


class UserResponse(BaseSchema):
    """Schema for returning a user profile."""

    id: str
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool
