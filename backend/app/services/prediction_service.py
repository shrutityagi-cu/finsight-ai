from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


from app.ml.feature_engineering import build_features_from_history
from app.ml.model_registry import ModelRegistry
from app.models import (
    HistoricalPrice,
    MLModel,
    MarketSymbol,
    Prediction,
    PredictionExplanation,
)
from app.schemas.prediction import (
    PredictionCreate,
    PredictionExplanationResponse,
    PredictionListResponse,
    PredictionResponse,
    PredictionUpdate,
)

logger = logging.getLogger(__name__)


class PredictionService:


    @staticmethod
    def _validate_pagination(page: int, page_size: int) -> tuple[int, int]:
        if page < 0:
            raise HTTPException(status_code=400, detail="page must be >= 0")
        if page_size <= 0 or page_size > 100:
            raise HTTPException(status_code=400, detail="page_size must be between 1 and 100")
        return page, page_size

    @staticmethod
    def _normalize_predicted_direction(direction: str) -> str:
        return direction.strip().lower()

    @staticmethod
    def _validate_sort(sort_by: str, sort_order: str):
        sort_order = (sort_order or "desc").lower()
        if sort_order not in {"asc", "desc"}:
            raise HTTPException(status_code=400, detail="Invalid sort_order (use asc|desc)")

        valid = {
            "created_at": Prediction.created_at,
            "confidence_score": Prediction.confidence_score,
        }
        if sort_by not in valid:
            raise HTTPException(status_code=400, detail="Invalid sort_by")

        col = valid[sort_by]
        return col.asc() if sort_order == "asc" else col.desc()

    @staticmethod
    async def _ensure_symbol_exists(db: AsyncSession, symbol_id: UUID) -> None:
        res = await db.execute(select(MarketSymbol).where(MarketSymbol.id == symbol_id).limit(1))
        if res.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="MarketSymbol not found")

    @staticmethod
    async def _ensure_model_exists(db: AsyncSession, model_id: UUID) -> None:
        res = await db.execute(select(MLModel).where(MLModel.id == model_id).limit(1))
        if res.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="MLModel not found")

    @staticmethod
    async def get_by_id(db: AsyncSession, *, prediction_id: UUID) -> Optional[Prediction]:
        stmt = select(Prediction).where(Prediction.id == prediction_id).limit(1)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        *,
        symbol_id: Optional[UUID],
        ticker: Optional[str],
        model_id: Optional[UUID],
        prediction_horizon: Optional[str],
        predicted_direction: Optional[str],
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Prediction], int, int, int]:
        page, page_size = PredictionService._validate_pagination(page=page, page_size=page_size)
        offset = page * page_size

        filters = []

        if symbol_id is not None:
            filters.append(Prediction.symbol_id == symbol_id)

        if model_id is not None:
            filters.append(Prediction.model_id == model_id)

        if prediction_horizon is not None:
            filters.append(Prediction.prediction_horizon == prediction_horizon.strip())

        if predicted_direction is not None:
            d = PredictionService._normalize_predicted_direction(predicted_direction)
            if d not in {"up", "down", "neutral"}:
                raise HTTPException(status_code=400, detail="predicted_direction must be up|down|neutral")
            filters.append(Prediction.predicted_direction == d)

        if ticker is not None and ticker.strip():
            # Filter by symbol's ticker, via relationship join using ORM columns
            # (No raw SQL; SQLAlchemy builds join)
            from sqlalchemy.orm import aliased

            symbol_alias = aliased(MarketSymbol)
            filters.append(
                Prediction.symbol_id == symbol_alias.id
            )
        # Use explicit join only if ticker filter is used
        order_clause = PredictionService._validate_sort(sort_by=sort_by, sort_order=sort_order)

        if ticker is not None and ticker.strip():
            t = ticker.strip().upper()
            join_stmt = (
                select(Prediction, MarketSymbol.ticker)
                .join(MarketSymbol, MarketSymbol.id == Prediction.symbol_id)
            )
            join_filters = [MarketSymbol.ticker == t]
            if symbol_id is not None:
                join_filters.append(Prediction.symbol_id == symbol_id)
            if model_id is not None:
                join_filters.append(Prediction.model_id == model_id)
            if prediction_horizon is not None:
                join_filters.append(Prediction.prediction_horizon == prediction_horizon.strip())
            if predicted_direction is not None:
                d = PredictionService._normalize_predicted_direction(predicted_direction)
                if d not in {"up", "down", "neutral"}:
                    raise HTTPException(status_code=400, detail="predicted_direction must be up|down|neutral")
                join_filters.append(Prediction.predicted_direction == d)

            count_stmt = (
                select(func.count())
                .select_from(Prediction)
                .join(MarketSymbol, MarketSymbol.id == Prediction.symbol_id)
                .where(*join_filters)
            )
            count_res = await db.execute(count_stmt)
            total = int(count_res.scalar_one())

            items_stmt = (
                select(Prediction)
                .join(MarketSymbol, MarketSymbol.id == Prediction.symbol_id)
                .where(*join_filters)
                .order_by(order_clause)
                .offset(offset)
                .limit(page_size)
            )
            items_res = await db.execute(items_stmt)
            items = list(items_res.scalars().all())
            return items, total, page, page_size

        # No ticker join required
        base_count = select(func.count()).select_from(Prediction)
        if filters:
            base_count = base_count.where(*filters)
        count_res = await db.execute(base_count)
        total = int(count_res.scalar_one())

        stmt = select(Prediction).order_by(order_clause)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.offset(offset).limit(page_size)

        res = await db.execute(stmt)
        items = list(res.scalars().all())
        return items, total, page, page_size

    @staticmethod
    async def create(db: AsyncSession, *, current_in: PredictionCreate) -> Prediction:
        predicted_direction = PredictionService._normalize_predicted_direction(current_in.predicted_direction)
        if predicted_direction not in {"up", "down", "neutral"}:
            raise HTTPException(status_code=400, detail="predicted_direction must be up|down|neutral")

        # Validate FKs exist
        await PredictionService._ensure_symbol_exists(db, current_in.symbol_id)
        await PredictionService._ensure_model_exists(db, current_in.model_id)

        pred = Prediction(
            symbol_id=current_in.symbol_id,
            model_id=current_in.model_id,
            prediction_horizon=current_in.prediction_horizon.strip(),
            predicted_direction=predicted_direction,
            confidence_score=current_in.confidence_score,
            created_at=current_in.model_dump().get("created_at", None) or None,  # will be ignored by DB? see note below
        )
        # created_at is NOT nullable in ORM; we must set it.
        # Overwrite properly:
        from datetime import datetime, timezone

        pred.created_at = datetime.now(timezone.utc)

        db.add(pred)
        await db.commit()
        await db.refresh(pred)
        return pred

    @staticmethod
    async def update(
        db: AsyncSession, *, prediction_id: UUID, update_in: PredictionUpdate
    ) -> Prediction:

        res = await db.execute(select(Prediction).where(Prediction.id == prediction_id).limit(1))
        pred = res.scalar_one_or_none()
        if pred is None:
            raise HTTPException(status_code=404, detail="Prediction not found")

        if update_in.symbol_id is not None:
            await PredictionService._ensure_symbol_exists(db, update_in.symbol_id)
            pred.symbol_id = update_in.symbol_id

        if update_in.model_id is not None:
            await PredictionService._ensure_model_exists(db, update_in.model_id)
            pred.model_id = update_in.model_id

        if update_in.prediction_horizon is not None:
            pred.prediction_horizon = update_in.prediction_horizon.strip()

        if update_in.predicted_direction is not None:
            predicted_direction = PredictionService._normalize_predicted_direction(update_in.predicted_direction)
            if predicted_direction not in {"up", "down", "neutral"}:
                raise HTTPException(status_code=400, detail="predicted_direction must be up|down|neutral")
            pred.predicted_direction = predicted_direction

        if update_in.confidence_score is not None:
            pred.confidence_score = update_in.confidence_score

        await db.commit()
        await db.refresh(pred)
        return pred

    @staticmethod
    async def delete(db: AsyncSession, *, prediction_id: UUID) -> None:
        res = await db.execute(select(Prediction).where(Prediction.id == prediction_id).limit(1))
        pred = res.scalar_one_or_none()
        if pred is None:
            raise HTTPException(status_code=404, detail="Prediction not found")

        await db.delete(pred)
        await db.commit()
