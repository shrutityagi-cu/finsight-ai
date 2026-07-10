from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_symbol import MarketSymbol
from app.models.portfolio import Portfolio
from app.models.portfolio_transaction import PortfolioTransaction
from app.models.historical_price import HistoricalPrice
from app.services.historical_price_service import HistoricalPriceService
from app.schemas.historical_price import HistoricalPriceRefreshRequest


@dataclass(frozen=True)
class _Holding:
    """Per-symbol computed holding used for portfolio-level aggregation."""

    symbol_id: UUID
    ticker: str
    sector: Optional[str]
    quantity: float
    cost_basis: float
    avg_buy_price: float
    current_price: float
    market_value: float


def _safe_pct(numerator: float, denominator: float) -> float:
    """Compute percentage safely.

    Args:
        numerator: Numerator value.
        denominator: Denominator value.

    Returns:
        Percentage in range (0..100) if computable; otherwise 0.0.
    """

    if denominator == 0:
        return 0.0
    return float((numerator / denominator) * 100.0)


def _round2(value: float) -> float:
    """Round to two decimals for stable JSON output."""

    # Avoid -0.0
    v = round(value, 2)
    return 0.0 if v == -0.0 else v


async def _get_user_portfolio(
    *,
    db: AsyncSession,
    portfolio_id: UUID,
    current_user: Any,
) -> Portfolio:
    """Fetch portfolio ensuring it belongs to the current user.

    Args:
        db: Async SQLAlchemy session.
        portfolio_id: Portfolio id to analyze.
        current_user: Authenticated user object.

    Returns:
        Portfolio ORM instance.

    Raises:
        HTTPException(404): if portfolio is missing or not owned by user.
    """

    current_user_id = getattr(current_user, "id", None)
    if current_user_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    stmt: Select[tuple[Portfolio]] = (
        select(Portfolio)
        .where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user_id,
            Portfolio.deleted_at.is_(None),
        )
        .limit(1)
    )
    res = await db.execute(stmt)
    portfolio = res.scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


async def _get_symbol_aggregates(
    *,
    db: AsyncSession,
    portfolio_id: UUID,
) -> list[tuple[UUID, str, Optional[str], float, float]]:
    """Compute net quantities and cost basis per symbol using transaction rows.

    Interpretation:
    - quantity_signed is +quantity for BUY and -quantity for SELL.
    - cost_basis is accumulated as (unit_price * quantity + fees) for BUY,
      and subtracted similarly for SELL to reflect reduced exposure.

    Args:
        db: Async SQLAlchemy session.
        portfolio_id: Portfolio id.

    Returns:
        List of tuples:
            (symbol_id, ticker, sector, net_quantity, cost_basis)

        Only symbols with non-zero net_quantity are returned.
    """

    t = PortfolioTransaction

    quantity_signed = func.sum(
        func.case((t.transaction_type == "SELL", -t.quantity), else_=t.quantity)
    )

    txn_amount = (t.unit_price * t.quantity) + t.fees

    # Subtract BUY/Sell contributions symmetrically so cost_basis tracks remaining lots approximately.
    cost_basis = func.sum(
        func.case((t.transaction_type == "SELL", -txn_amount), else_=txn_amount)
    )

    stmt = (
        select(
            MarketSymbol.id,
            MarketSymbol.ticker,
            MarketSymbol.sector,
            quantity_signed.label("net_quantity"),
            cost_basis.label("cost_basis"),
        )
        .join_from(t, MarketSymbol, t.symbol_id == MarketSymbol.id)
        .where(t.portfolio_id == portfolio_id)
        .group_by(MarketSymbol.id, MarketSymbol.ticker, MarketSymbol.sector)
        .having(quantity_signed != 0)
    )

    res = await db.execute(stmt)
    rows = res.all()
    return [
        (row.id, row.ticker, row.sector, float(row.net_quantity), float(row.cost_basis))
        for row in rows
    ]


async def _get_latest_prices_by_symbol(
    *,
    db: AsyncSession,
    symbol_ids: list[UUID],
    tickers: list[str],
) -> dict[UUID, float]:
    """Return latest close_price for each symbol id.

    Uses HistoricalPrice cache; if missing for any symbol, triggers refresh
    through HistoricalPriceService.

    Args:
        db: Async SQLAlchemy session.
        symbol_ids: MarketSymbol ids.
        tickers: MarketSymbol tickers (aligned with symbol_ids).

    Returns:
        Mapping {symbol_id: latest_close_price}.

    Raises:
        HTTPException(503): if market data is unavailable after refresh.
    """

    if not symbol_ids:
        return {}

    # Step 1: max as_of per symbol
    max_stmt = (
        select(HistoricalPrice.symbol_id, func.max(HistoricalPrice.as_of).label("as_of"))
        .where(HistoricalPrice.symbol_id.in_(symbol_ids))
        .group_by(HistoricalPrice.symbol_id)
    )
    max_res = await db.execute(max_stmt)
    asof_rows = max_res.all()
    asof_map: dict[UUID, Any] = {r.symbol_id: r.as_of for r in asof_rows}

    price_map: dict[UUID, float] = {}
    missing: list[tuple[UUID, str]] = []

    for sid, ticker in zip(symbol_ids, tickers):
        as_of = asof_map.get(sid)
        if as_of is None:
            missing.append((sid, ticker))
            continue
        price_res = await db.execute(
            select(HistoricalPrice.close_price).where(
                HistoricalPrice.symbol_id == sid,
                HistoricalPrice.as_of == as_of,
            )
        )
        price = price_res.scalar_one_or_none()
        if price is None:
            missing.append((sid, ticker))
            continue
        price_map[sid] = float(price)

    # Step 2: refresh missing
    if missing:
        req = HistoricalPriceRefreshRequest(period="daily")
        for sid, ticker in missing:
            try:
                await HistoricalPriceService.refresh_symbol(
                    db,
                    current_symbol_id=sid,
                    ticker=ticker,
                    req=req,
                )
            except HTTPException as exc:
                raise HTTPException(status_code=503, detail="Market data unavailable") from exc

        # Step 3: re-query after refresh
        max_res2 = await db.execute(max_stmt)
        asof_rows2 = max_res2.all()
        asof_map2: dict[UUID, Any] = {r.symbol_id: r.as_of for r in asof_rows2}

        for sid, _ticker in missing:
            as_of = asof_map2.get(sid)
            if as_of is None:
                raise HTTPException(status_code=503, detail="Market data unavailable")
            close_res = await db.execute(
                select(HistoricalPrice.close_price).where(
                    HistoricalPrice.symbol_id == sid,
                    HistoricalPrice.as_of == as_of,
                )
            )
            close_price = close_res.scalar_one_or_none()
            if close_price is None:
                raise HTTPException(status_code=503, detail="Market data unavailable")
            price_map[sid] = float(close_price)

    return price_map


async def _compute_holdings(
    *,
    db: AsyncSession,
    portfolio_id: UUID,
) -> list[_Holding]:
    """Compute per-symbol holdings with market value based on latest prices."""

    aggregates = await _get_symbol_aggregates(db=db, portfolio_id=portfolio_id)
    if not aggregates:
        return []

    symbol_ids = [a[0] for a in aggregates]
    tickers = [a[1] for a in aggregates]

    prices = await _get_latest_prices_by_symbol(
        db=db,
        symbol_ids=symbol_ids,
        tickers=tickers,
    )

    holdings: list[_Holding] = []
    for symbol_id, ticker, sector, net_quantity, cost_basis in aggregates:
        current_price = prices.get(symbol_id)
        if current_price is None:
            # Should be unreachable due to refresh logic.
            raise HTTPException(status_code=503, detail="Market data unavailable")

        market_value = net_quantity * current_price
        avg_buy_price = 0.0 if net_quantity == 0 else (cost_basis / net_quantity)

        holdings.append(
            _Holding(
                symbol_id=symbol_id,
                ticker=ticker,
                sector=sector,
                quantity=net_quantity,
                cost_basis=cost_basis,
                avg_buy_price=avg_buy_price,
                current_price=current_price,
                market_value=market_value,
            )
        )

    return holdings


def _compute_average_position_size(holdings: list[_Holding]) -> float:
    """Average position size measured by market value per holding."""

    if not holdings:
        return 0.0
    return float(sum(h.market_value for h in holdings) / len(holdings))


def _compute_cash_allocation(total_portfolio_value: float, holdings_market_value: float) -> float:
    """Compute cash allocation as residual.

    Since the schema does not define an explicit cash account, cash allocation is
    treated as residual value:
        cash_value = total_portfolio_value - sum(holding_market_values)

    In an unmodified engine, total_portfolio_value is defined as sum of market
    values of all holdings. Therefore cash allocation becomes 0.0 unless
    additional cash lines exist via transactions (not modeled in current schema).
    """

    # With the current data model (no explicit cash), cash residual should be 0.
    # We still compute generically for robustness.
    return float(total_portfolio_value - holdings_market_value)


def _top_holdings(holdings: list[_Holding], n: int) -> list[dict[str, Any]]:
    """Return top N holdings by market value."""

    sorted_holdings = sorted(holdings, key=lambda h: h.market_value, reverse=True)
    top = sorted_holdings[:n]
    return [
        {
            "ticker": h.ticker,
            "market_value": _round2(h.market_value),
            "allocation_pct": _round2(h.market_value),
            "quantity": _round2(h.quantity),
            "sector": h.sector,
        }
        for h in top
    ]


async def analyze_portfolio_intelligence(
    *,
    portfolio_id: UUID,
    db: AsyncSession,
    current_user: Any,
) -> dict[str, Any]:
    """Portfolio Intelligence Engine.

    Computes key portfolio statistics using existing ORM models.

    Metrics:
      - total_portfolio_value
      - number_of_holdings
      - allocation_pct (per holding)
      - largest_holding
      - cash_allocation
      - average_position_size
      - top_5_holdings
      - sector_exposure

    Args:
        portfolio_id: Portfolio id to analyze.
        db: Async SQLAlchemy session.
        current_user: Authenticated user (must include `id`).

    Returns:
        Pydantic-compatible dictionary containing computed metrics.

    Raises:
        HTTPException: if portfolio is missing or market data unavailable.
    """

    _ = await _get_user_portfolio(db=db, portfolio_id=portfolio_id, current_user=current_user)

    holdings = await _compute_holdings(db=db, portfolio_id=portfolio_id)

    # Total portfolio value: market value sum of holdings (no explicit cash model).
    holdings_market_value = float(sum(h.market_value for h in holdings))
    total_portfolio_value = holdings_market_value

    number_of_holdings = len(holdings)

    if total_portfolio_value == 0:
        largest_holding: Optional[dict[str, Any]] = None
        average_position_size = 0.0
        cash_allocation = 0.0
        top_5: list[dict[str, Any]] = []
        sector_rows: list[dict[str, Any]] = []
    else:
        # Largest holding
        sorted_holdings = sorted(holdings, key=lambda h: h.market_value, reverse=True)
        largest = sorted_holdings[0]
        largest_holding = {
            "ticker": largest.ticker,
            "market_value": _round2(largest.market_value),
            "allocation_pct": _round2(_safe_pct(largest.market_value, total_portfolio_value)),
            "sector": largest.sector,
        }

        average_position_size = _round2(_compute_average_position_size(sorted_holdings))

        # Cash allocation residual
        cash_allocation = _round2(
            _compute_cash_allocation(
                total_portfolio_value=total_portfolio_value,
                holdings_market_value=holdings_market_value,
            )
        )

        # Top 5 holdings with allocation %
        top = sorted_holdings[:5]
        top_5 = [
            {
                "ticker": h.ticker,
                "market_value": _round2(h.market_value),
                "allocation_pct": _round2(_safe_pct(h.market_value, total_portfolio_value)),
                "quantity": _round2(h.quantity),
                "sector": h.sector,
            }
            for h in top
        ]

        # Sector exposure
        sector_map: dict[str, float] = {}
        for h in holdings:
            sector = h.sector or "Unknown"
            sector_map[sector] = sector_map.get(sector, 0.0) + h.market_value

        sector_rows = [
            {
                "sector": sector,
                "current_value": _round2(value),
                "allocation_pct": _round2(_safe_pct(value, total_portfolio_value)),
            }
            for sector, value in sector_map.items()
        ]
        sector_rows.sort(key=lambda r: r["current_value"], reverse=True)

    allocation_pct_rows = [
        {
            "ticker": h.ticker,
            "allocation_pct": _round2(_safe_pct(h.market_value, total_portfolio_value)),
            "market_value": _round2(h.market_value),
            "sector": h.sector,
        }
        for h in sorted(holdings, key=lambda x: x.market_value, reverse=True)
    ]

    return {
        "total_portfolio_value": _round2(total_portfolio_value),
        "number_of_holdings": number_of_holdings,
        "allocation_pct": allocation_pct_rows,
        "largest_holding": largest_holding,
        "cash_allocation": cash_allocation,
        "average_position_size": average_position_size,
        "top_5_holdings": top_5,
        "sector_exposure": sector_rows,
    }

