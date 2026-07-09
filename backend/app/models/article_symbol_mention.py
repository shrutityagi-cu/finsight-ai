from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ArticleSymbolMention(Base):
    __tablename__ = "article_symbol_mentions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("news_articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("market_symbols.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    article: Mapped["NewsArticle"] = relationship(back_populates="symbol_mentions")
    symbol: Mapped["MarketSymbol"] = relationship(back_populates="article_mentions")

    __table_args__ = (
        UniqueConstraint("article_id", "symbol_id", name="uq_article_symbol_mention"),
    )
