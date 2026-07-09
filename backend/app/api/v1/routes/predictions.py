from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models import User
from app.core.dependencies import get_current_active_user
from app.schemas.prediction import (
    PredictionCreate,
    PredictionListResponse,
    PredictionResponse,
    PredictionUpdate,
)
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("", response_model=PredictionListResponse)
async def list_predictions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    symbol_id: Optional[UUID] = Query(default=None),
    ticker: Optional[str] = Query(default=None, description="Filter by MarketSymbol.ticker (partial, case-insensitive)"),
    model_id: Optional[UUID] = Query(default=None),
    prediction_horizon: Optional[str] = Query(default=None),
    predicted_direction: Optional[str] = Query(default=None),
    page: int = Query(default=0, ge=0),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
) -> PredictionListResponse:
    items, total, page, page_size = await PredictionService.list(
        db,
        symbol_id=symbol_id,
        ticker=ticker,
        model_id=model_id,
        prediction_horizon=prediction_horizon,
        predicted_direction=predicted_direction,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PredictionListResponse(
        items=[PredictionResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PredictionResponse:
    try:
        pid = UUID(prediction_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id") from exc

    pred = await PredictionService.get_by_id(db, prediction_id=pid)
    if pred is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return PredictionResponse.model_validate(pred)


@router.post("", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
async def create_prediction(
    prediction_in: PredictionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PredictionResponse:
    pred = await PredictionService.create(db, current_in=prediction_in)
    return PredictionResponse.model_validate(pred)


@router.patch("/{prediction_id}", response_model=PredictionResponse)
async def update_prediction(
    prediction_id: str,
    prediction_in: PredictionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PredictionResponse:
    try:
        pid = UUID(prediction_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id") from exc

    pred = await PredictionService.update(db, prediction_id=pid, update_in=prediction_in)
    return PredictionResponse.model_validate(pred)


@router.delete("/{prediction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prediction(
    prediction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    try:
        pid = UUID(prediction_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id") from exc

    await PredictionService.delete(db, prediction_id=pid)
