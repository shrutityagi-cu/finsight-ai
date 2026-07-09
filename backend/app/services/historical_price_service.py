from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import yfinance as yf
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HistoricalPrice, MarketSymbol
from app.schemas.historical_price import HistoricalPriceRefreshRequest

logger = logging.getLogger(__name__)


class HistoricalPriceService:
    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        return ticker.strip().upper()

    @staticmethod
    def _validate_period(period: str) -> str:
        if period not in {"daily", "weekly", "monthly"}:
            raise HTTPException(status_code=400, detail="Invalid period")
        return period

    @staticmethod
    def _default_range_for_period(period: str) -> tuple[date, date]:
        now = datetime.now(timezone.utc).date()
        if period == "daily":
            start = now - timedelta(days=365)
        elif period == "weekly":
            start = now - timedelta(days=365 * 2)
        else:  # monthly
            start = now - timedelta(days=365 * 5)
        return start, now

    @staticmethod
    def _validate_date_range(
        *, period: str, start_date: Optional[date], end_date: Optional[date]
    ) -> tuple[date, date]:
        start, end = HistoricalPriceService._default_range_for_period(period)
        if start_date is not None:
            start = start_date
        if end_date is not None:
            end = end_date
        if start > end:
            raise HTTPException(status_code=400, detail="Invalid date range")
        return start, end

    @staticmethod
    def _map_yf_period_to_interval(period: str) -> str:
        # yfinance uses interval strings; for monthly we use 1mo, weekly 1wk.
        if period == "daily":
            return "1d"
        if period == "weekly":
            return "1wk"
        return "1mo"

    @staticmethod
    async def _get_symbol_or_404(db: AsyncSession, *, ticker: str) -> MarketSymbol:
        t = HistoricalPriceService._normalize_ticker(ticker)
        res = await db.execute(select(MarketSymbol).where(MarketSymbol.ticker == t).limit(1))
        sym = res.scalar_one_or_none()
        if sym is None:
            raise HTTPException(status_code=404, detail="Ticker not found")
        return sym

    @staticmethod
    def _dataframe_to_rows(symbol_id: UUID, df) -> list[HistoricalPrice]:
        if df is None or df.empty:
            return []

        rows: list[HistoricalPrice] = []
        # yfinance returns DatetimeIndex.
        for idx, rec in df.iterrows():
            if rec is None:
                continue
            # idx may be Timestamp; store as aware datetime at midnight.
            if isinstance(idx, datetime):
                as_of = idx.replace(tzinfo=timezone.utc) if idx.tzinfo is None else idx
            else:
                as_of = datetime.fromtimestamp(float(idx), tz=timezone.utc)

            rows.append(
                HistoricalPrice(
                    symbol_id=symbol_id,
                    as_of=as_of,
                    open_price=float(rec.get("Open")),
                    high_price=float(rec.get("High")),
                    low_price=float(rec.get("Low")),
                    close_price=float(rec.get("Close")),
                    volume=int(rec.get("Volume") or 0),
                )
            )
        return rows

    @staticmethod
    async def bulk_insert(db: AsyncSession, *, rows: list[HistoricalPrice]) -> int:
        if not rows:
            return 0

        symbol_id = rows[0].symbol_id
        as_of_values = [r.as_of for r in rows]

        # Fetch existing keys to avoid duplicates in DB.
        existing_stmt = (
            select(HistoricalPrice.as_of)
            .where(HistoricalPrice.symbol_id == symbol_id)
            .where(HistoricalPrice.as_of.in_(as_of_values))
        )
        existing_res = await db.execute(existing_stmt)
        existing = set(existing_res.scalars().all())

        to_add = [r for r in rows if r.as_of not in existing]
        if not to_add:
            return 0

        db.add_all(to_add)
        await db.commit()
        return len(to_add)

    @staticmethod
    async def refresh_symbol(
        db: AsyncSession, *, current_symbol_id: UUID, ticker: str, req: HistoricalPriceRefreshRequest
    ) -> int:
        period = HistoricalPriceService._validate_period(req.period)
        start_date, end_date = HistoricalPriceService._validate_date_range(
            period=period, start_date=req.start_date, end_date=req.end_date
        )

        interval = HistoricalPriceService._map_yf_period_to_interval(period)
        # yfinance expects string dates.
        start_str = start_date.isoformat()
        end_str = (end_date + timedelta(days=1)).isoformat()  # inclusive-ish

        try:
            yf_ticker = yf.Ticker(HistoricalPriceService._normalize_ticker(ticker))
            # group_by ensures we get OHLCV columns.
            df = yf_ticker.history(
                start=start_str,
                end=end_str,
                interval=interval,
                auto_adjust=False,
                actions=False,
            )
        except Exception as exc:
            logger.exception("yfinance failure ticker=%s", ticker)
            raise HTTPException(status_code=502, detail="Failed to fetch from Yahoo Finance") from exc

        rows = HistoricalPriceService._dataframe_to_rows(current_symbol_id, df)
        return await HistoricalPriceService.bulk_insert(db, rows=rows)

    @staticmethod
    async def refresh_all(
        db: AsyncSession, *, req: HistoricalPriceRefreshRequest
    ) -> int:
        period = HistoricalPriceService._validate_period(req.period)
        _start_date, _end_date = HistoricalPriceService._validate_date_range(
            period=period, start_date=req.start_date, end_date=req.end_date
        )

        # List all symbols.
        res = await db.execute(select(MarketSymbol.id, MarketSymbol.ticker).where(MarketSymbol.is_active.is_(True)))
        symbols = res.all()

        total_inserted = 0
        for sym_id, ticker in symbols:
            total_inserted += await HistoricalPriceService.refresh_symbol(
                db, current_symbol_id=sym_id, ticker=ticker, req=req
            )
        return total_inserted

    @staticmethod
    async def get_history(
        db: AsyncSession,
        *,
        current_symbol_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 0,
        page_size: int = 100,
        sort_desc: bool = True,
    ) -> tuple[list[HistoricalPrice], int]:
        if page < 0 or page_size <= 0 or page_size > 1000:
            raise HTTPException(status_code=400, detail="Invalid pagination")

        stmt = select(HistoricalPrice).where(HistoricalPrice.symbol_id == current_symbol_id)
        if start_date is not None:
            stmt = stmt.where(HistoricalPrice.as_of >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
        if end_date is not None:
            stmt = stmt.where(HistoricalPrice.as_of <= datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc))

        count_stmt = select(func.count()).select_from(HistoricalPrice).where(HistoricalPrice.symbol_id == current_symbol_id)
        if start_date is not None:
            count_stmt = count_stmt.where(HistoricalPrice.as_of >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
        if end_date is not None:
            count_stmt = count_stmt.where(HistoricalPrice.as_of <= datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc))

        count_res = await db.execute(count_stmt)
        total = int(count_res.scalar_one())

        order = HistoricalPrice.as_of.desc() if sort_desc else HistoricalPrice.as_of.asc()
        stmt = stmt.order_by(order).offset(page * page_size).limit(page_size)

        res = await db.execute(stmt)
        return list(res.scalars().all()), total

    @staticmethod
    async def get_latest_price(db: AsyncSession, *, current_symbol_id: UUID) -> Optional[HistoricalPrice]:
        stmt = (
            select(HistoricalPrice)
            .where(HistoricalPrice.symbol_id == current_symbol_id)
            .order_by(HistoricalPrice.as_of.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

