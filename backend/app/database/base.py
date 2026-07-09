"""
Database metadata.

Import every model here so SQLAlchemy knows every table before
Alembic generates migrations.
"""

from app.models import Base

# Import every model exactly once so Alembic registers them.
from app.models import (  # noqa: F401
    User,
    Role,
    UserRoleAssignment,
    Portfolio,
    PortfolioTransaction,
    Watchlist,
    WatchlistItem,
    MarketSymbol,
    HistoricalPrice,
    NewsArticle,
    ArticleSymbolMention,
    ArticleSentiment,
    MLModel,
    Prediction,
    PredictionExplanation,
    Conversation,
    ConversationMessage,
    RefreshToken,
    AuditLog,
)

target_metadata = Base.metadata
