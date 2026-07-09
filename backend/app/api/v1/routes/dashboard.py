from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.database.session import get_db
from app.models import Portfolio, User
from app.schemas.portfolio_analytics import (
    AllocationResponse,
    DashboardResponse,
    PerformanceResponse,
    PortfolioSummaryResponse,
    RiskMetricsResponse,
    SectorBreakdownResponse,
)
from app.services.portfolio_analytics_service import PortfolioIntelligenceService

router = APIRouter(prefix="/portfolio-intelligence", tags=["portfolio-intelligence"])


async def _get_current_default_portfolio(
    db: AsyncSession,
    *,
    current_user: User,
) -> Portfolio:
    stmt = (
        # lazy import avoided: we already import Portfolio
        # noqa: E501
        __import__("sqlalchemy").select(Portfolio)
        .where(
            Portfolio.user_id == current_user.id,
            Portfolio.deleted_at.is_(None),
            Portfolio.is_default.is_(True),
        )
        .limit(1)
    )
    res = await db.execute(stmt)
    portfolio = res.scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(status_code=404, detail="No default portfolio found for user.")
    return portfolio


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def portfolio_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioSummaryResponse:
    service = PortfolioIntelligenceService(db=db)
    summary = await service.get_summary(current_user_id=current_user.id)
    return PortfolioSummaryResponse(**summary)


from app.schemas.portfolio_analytics import HoldingResponse


@router.get("/holdings", response_model=list[HoldingResponse])
async def portfolio_holdings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[HoldingResponse]:
    service = PortfolioIntelligenceService(db=db)
    holdings = await service.get_holdings(current_user_id=current_user.id)
    return [HoldingResponse(**h) for h in holdings]



@router.get("/allocation", response_model=list[AllocationResponse])
async def asset_allocation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AllocationResponse]:
    service = PortfolioIntelligenceService(db=db)
    allocation = await service.get_asset_allocation(current_user_id=current_user.id)
    return [AllocationResponse(**a) for a in allocation]


@router.get("/performance", response_model=PerformanceResponse)
async def performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PerformanceResponse:
    service = PortfolioIntelligenceService(db=db)
    perf = await service.calculate_performance(current_user_id=current_user.id)
    return PerformanceResponse(**perf)


@router.get("/risk", response_model=RiskMetricsResponse)
async def risk(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RiskMetricsResponse:
    service = PortfolioIntelligenceService(db=db)
    risk_metrics = await service.calculate_risk_metrics(current_user_id=current_user.id)
    return RiskMetricsResponse(**risk_metrics)


@router.get("/sectors", response_model=list[SectorBreakdownResponse])
async def sectors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[SectorBreakdownResponse]:
    service = PortfolioIntelligenceService(db=db)
    sectors = await service.get_sector_breakdown(current_user_id=current_user.id)
    return [SectorBreakdownResponse(**s) for s in sectors]


@router.get("/", response_model=DashboardResponse)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DashboardResponse:
    service = PortfolioIntelligenceService(db=db)
    data = await service.build_dashboard(current_user_id=current_user.id)
    return DashboardResponse(**data)

