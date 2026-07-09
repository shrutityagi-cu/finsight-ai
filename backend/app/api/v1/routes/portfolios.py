from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.database.session import get_db
from app.models import User
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioResponse,
    PortfolioUpdate,
)
from app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[PortfolioResponse]:
    portfolios = await PortfolioService.list_portfolios_for_user(db, current_user=current_user)
    return [PortfolioResponse.model_validate(p) for p in portfolios]


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioResponse:
    from uuid import UUID

    try:
        pid = UUID(portfolio_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid portfolio id") from exc

    portfolio = await PortfolioService.get_portfolio_by_id_for_user(
        db, current_user=current_user, portfolio_id=pid
    )
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return PortfolioResponse.model_validate(portfolio)


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    portfolio_in: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioResponse:
    portfolio = await PortfolioService.create_portfolio(db, current_user=current_user, portfolio_in=portfolio_in)
    return PortfolioResponse.model_validate(portfolio)


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: str,
    portfolio_in: PortfolioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioResponse:
    from uuid import UUID

    try:
        pid = UUID(portfolio_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid portfolio id") from exc

    portfolio = await PortfolioService.update_portfolio(
        db,
        current_user=current_user,
        portfolio_id=pid,
        portfolio_in=portfolio_in,
    )
    return PortfolioResponse.model_validate(portfolio)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    from uuid import UUID

    try:
        pid = UUID(portfolio_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid portfolio id") from exc

    await PortfolioService.delete_portfolio(db, current_user=current_user, portfolio_id=pid)

