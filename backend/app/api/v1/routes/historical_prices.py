from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.database.session import get_db
from app.models import User
from app.schemas.historical_price import (
    HistoricalPriceListResponse,
    HistoricalPriceRefreshRequest,
    HistoricalPriceResponse,
)
from app.services.historical_price_service import HistoricalPriceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/historical-prices", tags=["historical-prices"])


def _parse_date(value: Optional[str], *, field: str) -> Optional[date]:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field}") from exc


@router.get("/{ticker}", response_model=HistoricalPriceListResponse)
async def get_history(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    page: int = Query(default=0, ge=0),
    page_size: int = Query(default=100, ge=1, le=500),
    sort: str = Query(default="desc", description="asc|desc"),
) -> HistoricalPriceListResponse:
    sd = _parse_date(start_date, field="start_date")
    ed = _parse_date(end_date, field="end_date")

    sym = await HistoricalPriceService._get_symbol_or_404(db, ticker=ticker)

    sort_desc = sort.lower() != "asc"
    items, total = await HistoricalPriceService.get_history(
        db,
        current_symbol_id=sym.id,
        start_date=sd,
        end_date=ed,
        page=page,
        page_size=page_size,
        sort_desc=sort_desc,
    )

    return HistoricalPriceListResponse(
        items=[HistoricalPriceResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{ticker}/latest", response_model=HistoricalPriceResponse)
async def get_latest(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> HistoricalPriceResponse:
    sym = await HistoricalPriceService._get_symbol_or_404(db, ticker=ticker)
    latest = await HistoricalPriceService.get_latest_price(db, current_symbol_id=sym.id)
    if latest is None:
        raise HTTPException(status_code=404, detail="No historical prices found")
    return HistoricalPriceResponse.model_validate(latest)


@router.post("/refresh/{ticker}")
async def refresh_symbol(
    ticker: str,
    req: HistoricalPriceRefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, int]:
    sym = await HistoricalPriceService._get_symbol_or_404(db, ticker=ticker)
    inserted = await HistoricalPriceService.refresh_symbol(
        db, current_symbol_id=sym.id, ticker=ticker, req=req
    )
    return {"inserted": inserted}


@router.post("/refresh-all")
async def refresh_all(
    req: HistoricalPriceRefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, int]:
    inserted = await HistoricalPriceService.refresh_all(db, req=req)
    return {"inserted": inserted}

