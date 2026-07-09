from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class PortfolioTransaction(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "portfolio_transactions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("market_symbols.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    fees: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, server_default="0")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, server_default="USD")
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="transactions")
    symbol: Mapped["MarketSymbol"] = relationship(back_populates="transactions")

    __table_args__ = (
        CheckConstraint("quantity <> 0", name="ck_portfolio_transactions_quantity_not_zero"),
        CheckConstraint("unit_price >= 0", name="ck_portfolio_transactions_unit_price_non_negative"),
        CheckConstraint("fees >= 0", name="ck_portfolio_transactions_fees_non_negative"),
    )
