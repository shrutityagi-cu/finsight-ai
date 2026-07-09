from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema


class PortfolioCreate(BaseSchema):
    """Schema for creating a portfolio."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=10_000)


class PortfolioUpdate(BaseSchema):
    """Schema for partial portfolio updates."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[Optional[str]] = Field(default=None, max_length=10_000)
    is_default: Optional[bool] = None


class PortfolioResponse(BaseSchema):
    """Schema for returning portfolio data."""

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    is_default: bool

    model_config = ConfigDict(from_attributes=True)

