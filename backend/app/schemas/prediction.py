from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema


class PredictionCreate(BaseSchema):
    symbol_id: UUID
    model_id: UUID
    prediction_horizon: str = Field(min_length=1, max_length=50)
    predicted_direction: str = Field(min_length=1, max_length=20)
    confidence_score: float = Field(ge=0.0, le=1.0)


class PredictionUpdate(BaseSchema):
    symbol_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    prediction_horizon: Optional[str] = Field(default=None, min_length=1, max_length=50)
    predicted_direction: Optional[str] = Field(default=None, min_length=1, max_length=20)
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class PredictionExplanationResponse(BaseSchema):
    id: UUID
    feature_name: str
    importance_score: float
    explanation_text: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictionResponse(BaseSchema):
    id: UUID
    symbol_id: UUID
    model_id: UUID
    prediction_horizon: str
    predicted_direction: str
    confidence_score: float
    created_at: datetime

    explanations: list[PredictionExplanationResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PredictionListResponse(BaseSchema):
    items: list[PredictionResponse]
    total: int
    page: int
    page_size: int

