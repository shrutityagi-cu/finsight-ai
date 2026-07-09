from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Portfolio, User
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate


class PortfolioService:
    """Service layer for portfolio CRUD operations."""

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.strip()

    @staticmethod
    async def get_portfolio_by_id_for_user(
        db: AsyncSession, *, current_user: User, portfolio_id: UUID
    ) -> Optional[Portfolio]:
        stmt = (
            select(Portfolio)
            .where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == current_user.id,
                Portfolio.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_portfolios_for_user(db: AsyncSession, *, current_user: User) -> list[Portfolio]:
        stmt = (
            select(Portfolio)
            .where(Portfolio.user_id == current_user.id, Portfolio.deleted_at.is_(None))
            .order_by(Portfolio.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_portfolio(
        db: AsyncSession, *, current_user: User, portfolio_in: PortfolioCreate
    ) -> Portfolio:
        name = PortfolioService._normalize_name(portfolio_in.name)
        if not name:
            raise HTTPException(status_code=400, detail="Portfolio name is required")

        # Reject duplicate names for active (non-deleted) portfolios.
        dup_stmt = select(Portfolio).where(
            Portfolio.user_id == current_user.id,
            Portfolio.name == name,
            Portfolio.deleted_at.is_(None),
        )
        dup_res = await db.execute(dup_stmt)
        existing = dup_res.scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Portfolio name already exists")

        now = datetime.now(timezone.utc)
        is_first = False
        first_check_stmt = select(Portfolio).where(
            Portfolio.user_id == current_user.id,
            Portfolio.deleted_at.is_(None),
        )
        first_check_res = await db.execute(first_check_stmt)
        is_first = first_check_res.scalars().first() is None

        # Default rule: if it's the first portfolio for the user, set is_default=True.
        new_portfolio = Portfolio(
            user_id=current_user.id,
            name=name,
            description=portfolio_in.description,
            is_default=is_first,
        )
        db.add(new_portfolio)
        await db.flush()

        # If is_default is being set to True in the future, we would need to unset others.
        # For create, only the first portfolio becomes default.

        await db.commit()
        await db.refresh(new_portfolio)
        return new_portfolio

    @staticmethod
    async def update_portfolio(
        db: AsyncSession,
        *,
        current_user: User,
        portfolio_id: UUID,
        portfolio_in: PortfolioUpdate,
    ) -> Portfolio:
        portfolio_stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id).limit(1)
        res = await db.execute(portfolio_stmt)
        portfolio = res.scalar_one_or_none()

        if portfolio is None:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        if portfolio.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        name: Optional[str] = portfolio_in.name
        description: object = portfolio_in.description
        is_default: Optional[bool] = portfolio_in.is_default

        if name is not None:
            normalized = PortfolioService._normalize_name(name)
            if not normalized:
                raise HTTPException(status_code=400, detail="Portfolio name is required")

            # Check duplicate active names for this user.
            dup_stmt = select(Portfolio).where(
                Portfolio.user_id == current_user.id,
                Portfolio.name == normalized,
                Portfolio.deleted_at.is_(None),
                Portfolio.id != portfolio_id,
            )
            dup_res = await db.execute(dup_stmt)
            if dup_res.scalar_one_or_none() is not None:
                raise HTTPException(status_code=409, detail="Portfolio name already exists")

            portfolio.name = normalized

        if description is not None:
            # description: Optional[Optional[str]] => allow explicit nulling.
            portfolio.description = description

        # PATCH cannot modify deleted portfolios (already checked).

        if is_default is not None:
            if is_default and not portfolio.is_default:
                # Unset previous default within the same transaction.
                unset_stmt = (
                    update(Portfolio)
                    .where(
                        Portfolio.user_id == current_user.id,
                        Portfolio.deleted_at.is_(None),
                        Portfolio.is_default.is_(True),
                        Portfolio.id != portfolio_id,
                    )
                    .values(is_default=False)
                )
                await db.execute(unset_stmt)
                portfolio.is_default = True

            elif not is_default and portfolio.is_default:
                # Ensure they are not disabling the only default portfolio.
                default_check_stmt = select(Portfolio).where(
                    Portfolio.user_id == current_user.id,
                    Portfolio.deleted_at.is_(None),
                    Portfolio.is_default.is_(True),
                )
                default_res = await db.execute(default_check_stmt)
                defaults = default_res.scalars().all()
                if len(defaults) <= 1:
                    raise HTTPException(status_code=400, detail="Cannot unset the only default portfolio")
                portfolio.is_default = False

        await db.commit()
        await db.refresh(portfolio)
        return portfolio

    @staticmethod
    async def delete_portfolio(db: AsyncSession, *, current_user: User, portfolio_id: UUID) -> None:
        portfolio_stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id).limit(1)
        res = await db.execute(portfolio_stmt)
        portfolio = res.scalar_one_or_none()

        if portfolio is None or portfolio.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        # Default Portfolio Rule: prevent deleting the only default portfolio.
        default_check_stmt = select(Portfolio).where(
            Portfolio.user_id == current_user.id,
            Portfolio.deleted_at.is_(None),
            Portfolio.is_default.is_(True),
        )
        default_res = await db.execute(default_check_stmt)
        defaults = default_res.scalars().all()
        if portfolio.is_default and len(defaults) <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the only default portfolio")

        portfolio.deleted_at = datetime.utcnow()
        await db.flush()
        await db.commit()


