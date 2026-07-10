from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional
from uuid import UUID


RiskFunc = Callable[..., Awaitable[dict[str, Any]]]
PortfolioFunc = Callable[..., Awaitable[dict[str, Any]]]
DiversificationFunc = Callable[..., Awaitable[dict[str, Any]]]


async def build_dashboard(
    *,
    portfolio_id: UUID,
    db: Any,
    current_user: Any,
    portfolio_analyzer: PortfolioFunc,
    risk_engine: RiskFunc,
    diversification_engine: DiversificationFunc,
    performance_engine: Optional[Callable[..., Awaitable[dict[str, Any]]]] = None,
    recommendations_engine: Optional[Callable[..., Awaitable[dict[str, Any]]]] = None,
    charts_engine: Optional[Callable[..., Awaitable[dict[str, Any]]]] = None,
    alerts_engine: Optional[Callable[..., Awaitable[dict[str, Any]]]] = None,
    # RiskEngine optional params (forwarded through to risk_engine)
    risk_lookback_days: int = 252,
    trading_days_per_year: int = 252,
    risk_free_rate_annual: float = 0.0,
    market_index_ticker: str = "SPY",
    refresh_if_missing_prices: bool = False,
) -> dict[str, Any]:
    """Orchestrate dashboard payload for portfolio analytics.

    This module only coordinates existing engines/services. It contains **no**
    financial calculations.

    Args:
        portfolio_id: Portfolio UUID.
        db: Async DB session (typically sqlalchemy.ext.asyncio.AsyncSession).
        current_user: Authenticated user object.
        portfolio_analyzer: Async callable that returns a dict for portfolio summary.
        risk_engine: Async callable that returns a dict for risk (e.g., risk score/metrics).
        diversification_engine: Async callable that returns a dict for diversification.
        performance_engine: Optional async callable for performance metrics.
        recommendations_engine: Optional async callable for recommendations.
        charts_engine: Optional async callable for chart data.
        alerts_engine: Optional async callable for alerts.
        risk_lookback_days: Forwarded to risk_engine.
        trading_days_per_year: Forwarded to risk_engine.
        risk_free_rate_annual: Forwarded to risk_engine.
        market_index_ticker: Forwarded to risk_engine.
        refresh_if_missing_prices: Forwarded to risk_engine and (where supported) diversification_engine.

    Returns:
        JSON-compatible payload:
        {
          portfolio_summary,
          performance,
          risk,
          diversification,
          recommendations,
          charts,
          alerts
        }

    Notes:
        - "performance", "recommendations", "charts", "alerts" default to empty dicts.
        - Dependency injection is used to keep this unit-test friendly.
    """

    # Core blocks (must exist)
    portfolio_summary = await portfolio_analyzer(
        portfolio_id=portfolio_id,
        db=db,
        current_user=current_user,
    )

    risk = await risk_engine(
        portfolio_id=portfolio_id,
        db=db,
        current_user=current_user,
        lookback_days=risk_lookback_days,
        trading_days_per_year=trading_days_per_year,
        risk_free_rate_annual=risk_free_rate_annual,
        market_index_ticker=market_index_ticker,
        refresh_if_missing_prices=refresh_if_missing_prices,
    )

    diversification = await diversification_engine(
        portfolio_id=portfolio_id,
        db=db,
        current_user=current_user,
        refresh_if_missing_prices=refresh_if_missing_prices,
    )

    performance: dict[str, Any] = {}
    if performance_engine is not None:
        performance = await performance_engine(
            portfolio_id=portfolio_id,
            db=db,
            current_user=current_user,
        )

    recommendations: dict[str, Any] = {}
    if recommendations_engine is not None:
        recommendations = await recommendations_engine(
            portfolio_id=portfolio_id,
            db=db,
            current_user=current_user,
            diversification=diversification,
            risk=risk,
            portfolio_summary=portfolio_summary,
        )

    charts: dict[str, Any] = {}
    if charts_engine is not None:
        charts = await charts_engine(
            portfolio_id=portfolio_id,
            db=db,
            current_user=current_user,
            diversification=diversification,
            risk=risk,
            portfolio_summary=portfolio_summary,
        )

    alerts: dict[str, Any] = {}
    if alerts_engine is not None:
        alerts = await alerts_engine(
            portfolio_id=portfolio_id,
            db=db,
            current_user=current_user,
            diversification=diversification,
            risk=risk,
            portfolio_summary=portfolio_summary,
        )

    return {
        "portfolio_summary": portfolio_summary,
        "performance": performance,
        "risk": risk,
        "diversification": diversification,
        "recommendations": recommendations,
        "charts": charts,
        "alerts": alerts,
    }


__all__ = ["build_dashboard"]

