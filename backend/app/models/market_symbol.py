from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class MarketSymbol(TimestampMixin, Base):
    __tablename__ = "market_symbols"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, server_default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    transactions: Mapped[list["PortfolioTransaction"]] = relationship(back_populates="symbol")
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(back_populates="symbol")
    historical_prices: Mapped[list["HistoricalPrice"]] = relationship(back_populates="symbol")
    article_mentions: Mapped[list["ArticleSymbolMention"]] = relationship(back_populates="symbol")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="symbol")
