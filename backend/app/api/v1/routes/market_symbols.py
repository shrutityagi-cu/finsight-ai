from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.database.session import get_db
from app.models import User
from app.schemas.market_symbol import (
    MarketSymbolCreate,
    MarketSymbolListResponse,
    MarketSymbolResponse,
    MarketSymbolUpdate,
)
from app.services.market_symbol_service import MarketSymbolService

router = APIRouter(prefix="/market-symbols", tags=["market-symbols"])


@router.get("", response_model=MarketSymbolListResponse)
async def list_market_symbols(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    q: Optional[str] = Query(default=None, description="Search against ticker and name"),
    ticker: Optional[str] = Query(default=None, description="Search by ticker (partial, case-insensitive)"),
    company_name: Optional[str] = Query(default=None, description="Search by company name (maps to name)"),
    exchange: Optional[str] = Query(default=None),
    sector: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    page: int = Query(default=0, ge=0),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
) -> MarketSymbolListResponse:
    items, total, page, page_size = await MarketSymbolService.list(
        db,
        q=q,
        ticker=ticker,
        company_name=company_name,
        exchange=exchange,
        sector=sector,
        is_active=is_active,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return MarketSymbolListResponse(
        items=[MarketSymbolResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{symbol_id}", response_model=MarketSymbolResponse)
async def get_market_symbol(
    symbol_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MarketSymbolResponse:
    from uuid import UUID

    try:
        sid = UUID(symbol_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id") from exc

    symbol = await MarketSymbolService.get_by_id(db, symbol_id=sid)
    if symbol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MarketSymbol not found")
    return MarketSymbolResponse.model_validate(symbol)


@router.post("", response_model=MarketSymbolResponse, status_code=status.HTTP_201_CREATED)
async def create_market_symbol(
    symbol_in: MarketSymbolCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MarketSymbolResponse:
    symbol = await MarketSymbolService.create(db, current_in=symbol_in)
    return MarketSymbolResponse.model_validate(symbol)


@router.patch("/{symbol_id}", response_model=MarketSymbolResponse)
async def update_market_symbol(
    symbol_id: str,
    symbol_in: MarketSymbolUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MarketSymbolResponse:
    from uuid import UUID

    try:
        sid = UUID(symbol_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id") from exc

    symbol = await MarketSymbolService.update(db, symbol_id=sid, update_in=symbol_in)
    return MarketSymbolResponse.model_validate(symbol)


@router.delete("/{symbol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_market_symbol(
    symbol_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    from uuid import UUID

    try:
        sid = UUID(symbol_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id") from exc

    await MarketSymbolService.delete(db, symbol_id=sid)
