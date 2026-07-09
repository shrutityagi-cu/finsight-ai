from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class HistoricalPrice(Base):
    __tablename__ = "historical_prices"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("market_symbols.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    open_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    high_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    low_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    close_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(Numeric(20, 0), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    symbol: Mapped["MarketSymbol"] = relationship(back_populates="historical_prices")

    __table_args__ = (
        UniqueConstraint("symbol_id", "as_of", name="uq_historical_prices_symbol_asof"),
    )
