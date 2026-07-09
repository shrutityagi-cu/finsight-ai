from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import MarketSymbol
from app.schemas.market_symbol import MarketSymbolCreate, MarketSymbolUpdate


class MarketSymbolService:
    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        return ticker.strip().upper()

    @staticmethod
    def _validate_pagination(page: int, page_size: int) -> tuple[int, int]:
        if page < 0:
            raise HTTPException(status_code=400, detail="page must be >= 0")
        if page_size <= 0:
            raise HTTPException(status_code=400, detail="page_size must be > 0")
        if page_size > 100:
            raise HTTPException(status_code=400, detail="page_size must be <= 100")
        return page, page_size

    @staticmethod
    def _order_clause(sort_by: str, sort_order: str):
        sort_order = (sort_order or "asc").lower()
        if sort_order not in {"asc", "desc"}:
            raise HTTPException(status_code=400, detail="Invalid sort_order (use asc|desc)")

        valid = {
            "ticker": MarketSymbol.ticker,
            "name": MarketSymbol.name,
            "exchange": MarketSymbol.exchange,
            "sector": MarketSymbol.sector,
            "created_at": MarketSymbol.created_at,
        }
        if sort_by not in valid:
            raise HTTPException(status_code=400, detail="Invalid sort_by")

        col = valid[sort_by]
        return col.asc() if sort_order == "asc" else col.desc()

    @staticmethod
    async def get_by_id(db: AsyncSession, *, symbol_id: UUID) -> Optional[MarketSymbol]:
        stmt = select(MarketSymbol).where(MarketSymbol.id == symbol_id).limit(1)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        *,
        q: Optional[str],
        ticker: Optional[str],
        company_name: Optional[str],
        exchange: Optional[str],
        sector: Optional[str],
        is_active: Optional[bool],
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[MarketSymbol], int, int, int]:
        page, page_size = MarketSymbolService._validate_pagination(page=page, page_size=page_size)
        offset = page * page_size

        filters = []
        # Explicit param support
        if ticker:
            t = MarketSymbolService._normalize_ticker(ticker)
            filters.append(MarketSymbol.ticker.ilike(f"%{t}%"))
        if company_name:
            filters.append(MarketSymbol.name.ilike(f"%{company_name.strip()}%"))
        if exchange:
            filters.append(MarketSymbol.exchange.ilike(f"%{exchange.strip()}%"))
        if sector:
            filters.append(MarketSymbol.sector.ilike(f"%{sector.strip()}%"))
        if is_active is not None:
            filters.append(MarketSymbol.is_active == is_active)

        # Optional generic query param
        if q:
            q_norm = q.strip()
            if q_norm:
                # Search q against ticker and name (company) per earlier requirement language
                filters.append(
                    or_(
                        MarketSymbol.ticker.ilike(f"%{q_norm}%"),
                        MarketSymbol.name.ilike(f"%{q_norm}%"),
                    )
                )

        where_clause = filters[0] if filters else None
        if len(filters) > 1:
            from sqlalchemy import and_

            where_clause = and_(*filters)

        order_by = MarketSymbolService._order_clause(sort_by=sort_by, sort_order=sort_order)

        count_stmt = select(func.count()).select_from(MarketSymbol)
        if where_clause is not None:
            count_stmt = count_stmt.where(where_clause)
        count_res = await db.execute(count_stmt)
        total = int(count_res.scalar_one())

        stmt = select(MarketSymbol).where(where_clause) if where_clause is not None else select(MarketSymbol)
        stmt = stmt.order_by(order_by).offset(offset).limit(page_size)

        res = await db.execute(stmt)
        items = list(res.scalars().all())
        return items, total, page, page_size

    @staticmethod
    async def create(db: AsyncSession, *, current_in: MarketSymbolCreate) -> MarketSymbol:
        ticker = MarketSymbolService._normalize_ticker(current_in.ticker)
        if not ticker:
            raise HTTPException(status_code=400, detail="ticker is required")

        # Reject duplicate ticker (existing unique constraint) - proactive
        dup_stmt = select(MarketSymbol).where(MarketSymbol.ticker == ticker).limit(1)
        dup_res = await db.execute(dup_stmt)
        if dup_res.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="ticker already exists")

        symbol = MarketSymbol(
            ticker=ticker,
            name=current_in.name.strip(),
            exchange=current_in.exchange.strip() if current_in.exchange is not None else None,
            sector=current_in.sector.strip() if current_in.sector is not None else None,
            currency=current_in.currency.strip(),
            is_active=True if current_in.is_active is None else current_in.is_active,
        )
        db.add(symbol)
        await db.commit()
        await db.refresh(symbol)
        return symbol

    @staticmethod
    async def update(
        db: AsyncSession, *, symbol_id: UUID, update_in: MarketSymbolUpdate
    ) -> MarketSymbol:
        stmt = select(MarketSymbol).where(MarketSymbol.id == symbol_id).limit(1)
        res = await db.execute(stmt)
        symbol = res.scalar_one_or_none()
        if symbol is None:
            raise HTTPException(status_code=404, detail="MarketSymbol not found")

        # Do not permit updates to PK/created_at/soft delete (if any). Model has no deleted_at.
        if update_in.ticker is not None:
            new_ticker = MarketSymbolService._normalize_ticker(update_in.ticker)
            if new_ticker != symbol.ticker:
                dup_stmt = select(MarketSymbol).where(MarketSymbol.ticker == new_ticker).limit(1)
                dup_res = await db.execute(dup_stmt)
                if dup_res.scalar_one_or_none() is not None:
                    raise HTTPException(status_code=409, detail="ticker already exists")
                symbol.ticker = new_ticker

        if update_in.name is not None:
            symbol.name = update_in.name.strip()

        if update_in.exchange is not None:
            symbol.exchange = update_in.exchange.strip()

        if update_in.sector is not None:
            symbol.sector = update_in.sector.strip()

        if update_in.currency is not None:
            symbol.currency = update_in.currency.strip()

        if update_in.is_active is not None:
            symbol.is_active = update_in.is_active

        await db.commit()
        await db.refresh(symbol)
        return symbol

    @staticmethod
    async def delete(db: AsyncSession, *, symbol_id: UUID) -> None:
        stmt = select(MarketSymbol).where(MarketSymbol.id == symbol_id).limit(1)
        res = await db.execute(stmt)
        symbol = res.scalar_one_or_none()
        if symbol is None:
            raise HTTPException(status_code=404, detail="MarketSymbol not found")

        # No SoftDeleteMixin on MarketSymbol; hard delete.
        await db.delete(symbol)
        await db.commit()
