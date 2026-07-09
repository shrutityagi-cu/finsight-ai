from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import ConfigDict

from app.schemas.base import BaseSchema


class PortfolioSummaryResponse(BaseSchema):
    total_portfolio_value: float
    total_cost_basis: float
    current_market_value: float
    unrealized_gain_loss: float
    realized_gain_loss: float
    overall_return_pct: float
    todays_return: float
    number_of_holdings: int
    cash_invested: float


class HoldingResponse(BaseSchema):
    ticker: str
    quantity: float
    average_buy_price: float
    current_price: float
    market_value: float
    cost_basis: float
    profit_loss: float
    profit_loss_pct: Optional[float] = None
    weight: float


class AllocationResponse(BaseSchema):
    allocation_pct: float
    current_value: float
    cost_basis: float
    weight: float
    sector: Optional[str] = None
    industry: Optional[str] = None


class SectorBreakdownResponse(BaseSchema):
    sector: str
    current_value: float
    allocation_pct: float


class PerformanceResponse(BaseSchema):
    daily_return: float
    weekly_return: float
    monthly_return: float
    yearly_return: float
    cagr: float
    rolling_returns: list[float]


class RiskMetricsResponse(BaseSchema):
    portfolio_volatility: float
    sharpe_ratio: float
    maximum_drawdown: float
    beta: Optional[float] = None
    diversification_score: float
    risk_score: float


class DashboardResponse(BaseSchema):
    summary: PortfolioSummaryResponse
    holdings: list[HoldingResponse]
    allocation: list[AllocationResponse]
    performance: PerformanceResponse
    risk: RiskMetricsResponse
    sectors: list[SectorBreakdownResponse]


__all__ = [
    "PortfolioSummaryResponse",
    "HoldingResponse",
    "AllocationResponse",
    "SectorBreakdownResponse",
    "PerformanceResponse",
    "RiskMetricsResponse",
    "DashboardResponse",
]

