from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema


class MarketSymbolCreate(BaseSchema):
    ticker: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    exchange: Optional[str] = Field(default=None, max_length=100)
    sector: Optional[str] = Field(default=None, max_length=100)
    currency: str = Field(..., min_length=1, max_length=10)
    is_active: Optional[bool] = None


class MarketSymbolUpdate(BaseSchema):
    ticker: Optional[str] = Field(default=None, min_length=1, max_length=20)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    exchange: Optional[str] = Field(default=None, max_length=100)
    sector: Optional[str] = Field(default=None, max_length=100)
    currency: Optional[str] = Field(default=None, min_length=1, max_length=10)
    is_active: Optional[bool] = None


class MarketSymbolResponse(BaseSchema):
    id: UUID
    ticker: str
    name: str
    exchange: Optional[str] = None
    sector: Optional[str] = None
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketSymbolListResponse(BaseSchema):
    items: list[MarketSymbolResponse]
    total: int
    page: int
    page_size: int
