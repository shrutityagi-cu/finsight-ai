from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("market_symbols.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ml_models.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    prediction_horizon: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_direction: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    symbol: Mapped["MarketSymbol"] = relationship(back_populates="predictions")
    model: Mapped["MLModel"] = relationship(back_populates="predictions")
    explanations: Mapped[list["PredictionExplanation"]] = relationship(
        back_populates="prediction",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("confidence_score BETWEEN 0 AND 1", name="ck_predictions_confidence_score_range"),
        CheckConstraint(
            "predicted_direction IN ('up', 'down', 'neutral')",
            name="ck_predictions_predicted_direction",
        ),
    )
