from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema


class WatchlistCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)


class WatchlistUpdate(BaseSchema):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    # No is_default flags; watchlist model only has name


class WatchlistResponse(BaseSchema):
    id: UUID
    user_id: UUID
    name: str
    item_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WatchlistItemCreate(BaseSchema):
    symbol_id: UUID


class WatchlistItemResponse(BaseSchema):
    id: UUID
    watchlist_id: UUID
    symbol_id: UUID
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WatchlistItemListResponse(BaseSchema):
    items: list[WatchlistItemResponse]
