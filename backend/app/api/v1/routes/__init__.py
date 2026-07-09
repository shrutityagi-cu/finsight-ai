"""API route package for version 1."""

from .auth import router as auth
from .dashboard import router as dashboard
from .health import router as health
from .historical_prices import router as historical_prices
from .market_symbols import router as market_symbols
from .portfolios import router as portfolios
from .predictions import router as predictions
from .watchlists import router as watchlists

__all__ = [
    "auth",
    "dashboard",
    "health",
    "historical_prices",
    "market_symbols",
    "portfolios",
    "predictions",
    "watchlists",
]


