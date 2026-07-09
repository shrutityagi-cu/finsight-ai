from __future__ import annotations

from datetime import datetime, date
from typing import Literal, Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema


class HistoricalPriceResponse(BaseSchema):
    id: UUID
    symbol_id: UUID
    as_of: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HistoricalPriceListResponse(BaseSchema):
    items: list[HistoricalPriceResponse]
    total: Optional[int] = None
    page: Optional[int] = None
    page_size: Optional[int] = None


class HistoricalPriceRefreshRequest(BaseSchema):
    period: Literal["daily", "weekly", "monthly"] = Field(default="daily")
    start_date: Optional[date] = None
    end_date: Optional[date] = None

