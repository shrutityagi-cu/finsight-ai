from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    watchlist_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("watchlists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("market_symbols.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    watchlist: Mapped["Watchlist"] = relationship(back_populates="items")
    symbol: Mapped["MarketSymbol"] = relationship(back_populates="watchlist_items")

    __table_args__ = (
        UniqueConstraint("watchlist_id", "symbol_id", name="uq_watchlist_items_watchlist_symbol"),
    )
