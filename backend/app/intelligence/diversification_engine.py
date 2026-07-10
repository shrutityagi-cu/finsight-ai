from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.historical_price import HistoricalPrice
from app.models.market_symbol import MarketSymbol
from app.models.portfolio import Portfolio
from app.models.portfolio_transaction import PortfolioTransaction
from app.services.historical_price_service import HistoricalPriceService
from app.schemas.historical_price import HistoricalPriceRefreshRequest


@dataclass(frozen=True)
class _Holding:
    symbol_id: UUID
    ticker: str
    sector: Optional[str]
    quantity: float
    cost_basis: float
    current_price: float
    market_value: float


def _safe_div(n: float, d: float) -> float:
    if d == 0:
        return 0.0
    return float(n / d)


def _safe_pct(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float((numerator / denominator) * 100.0)


def _clamp(v: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, v)))


def _round2(v: float) -> float:
    v2 = round(v, 2)
    return 0.0 if v2 == -0.0 else v2


async def _get_user_portfolio(*, db: AsyncSession, portfolio_id: UUID, current_user: Any) -> Portfolio:
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
    """Compute net quantity and approximate cost basis per symbol.

    - BUY: +quantity, add (unit_price * quantity + fees)
    - SELL: -quantity, subtract (unit_price * quantity + fees)

    Returns tuples:
        (symbol_id, ticker, sector, net_quantity, cost_basis)

    Only symbols with non-zero net_quantity are returned.
    """

    t = PortfolioTransaction

    quantity_signed = func.sum(func.case((t.transaction_type == "SELL", -t.quantity), else_=t.quantity))

    txn_amount = (t.unit_price * t.quantity) + t.fees
    cost_basis = func.sum(func.case((t.transaction_type == "SELL", -txn_amount), else_=txn_amount))

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
    refresh_if_missing: bool,
) -> dict[UUID, float]:
    """Return latest close_price for each symbol_id.

    Uses HistoricalPrice cache; optionally refreshes missing symbols.
    """

    if not symbol_ids:
        return {}

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

    if missing and refresh_if_missing:
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

        # Re-query max(as_of)
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

    if missing and not refresh_if_missing:
        # If price is missing and we are not allowed to refresh, treat as unavailable.
        raise HTTPException(status_code=503, detail="Market data unavailable")

    return price_map


async def _compute_holdings(
    *,
    db: AsyncSession,
    portfolio_id: UUID,
    refresh_if_missing_prices: bool,
) -> list[_Holding]:
    aggregates = await _get_symbol_aggregates(db=db, portfolio_id=portfolio_id)
    if not aggregates:
        return []

    symbol_ids = [a[0] for a in aggregates]
    tickers = [a[1] for a in aggregates]

    prices = await _get_latest_prices_by_symbol(
        db=db,
        symbol_ids=symbol_ids,
        tickers=tickers,
        refresh_if_missing=refresh_if_missing_prices,
    )

    holdings: list[_Holding] = []
    for symbol_id, ticker, sector, net_quantity, cost_basis in aggregates:
        current_price = prices.get(symbol_id)
        if current_price is None:
            raise HTTPException(status_code=503, detail="Market data unavailable")

        market_value = float(net_quantity * current_price)
        holdings.append(
            _Holding(
                symbol_id=symbol_id,
                ticker=ticker,
                sector=sector,
                quantity=float(net_quantity),
                cost_basis=float(cost_basis),
                current_price=float(current_price),
                market_value=market_value,
            )
        )

    # Filter out any pathological negative/zero market values from SELL-heavy positions.
    # This keeps the diversification math (weights) stable.
    positive = [h for h in holdings if h.market_value > 0]
    return positive


def _compute_hhi(weights: list[float]) -> float:
    """Herfindahl-Hirschman Index for a weight vector that sums to 1.

    HHI = sum(w_i^2)
    Range:
      - best diversification (equal weights, N holdings): 1/N
      - worst case (all weight in one): 1
    """

    if not weights:
        return 0.0
    return float(sum(w * w for w in weights))


def _diversification_score_from_hhi(hhi: float, n_holdings: int) -> float:
    if n_holdings <= 1:
        return 0.0

    best_hhi = 1.0 / float(n_holdings)
    worst_hhi = 1.0

    denom = worst_hhi - best_hhi
    if denom <= 0:
        return 0.0

    # score should be high when hhi is close to best_hhi
    # normalized_concentration = (hhi - best_hhi) / (worst_hhi - best_hhi)
    normalized = (hhi - best_hhi) / denom
    score = (1.0 - normalized) * 100.0
    return _clamp(score, 0.0, 100.0)


def _top_by_market_value(holdings: list[_Holding], n: int) -> list[_Holding]:
    return sorted(holdings, key=lambda h: h.market_value, reverse=True)[:n]


def _build_recommendations(
    *,
    holdings: list[_Holding],
    sector_allocation_pct: dict[str, float],
    largest_position_pct: float,
    hhi: float,
    diversification_score: float,
) -> list[str]:
    recommendations: list[str] = []

    n_holdings = len(holdings)
    top_holdings = _top_by_market_value(holdings, 3)

    # Thresholds tuned to common portfolio UX expectations.
    if largest_position_pct >= 30.0:
        top = top_holdings[0]
        recommendations.append(
            f"Reduce concentration in {top.ticker} ({largest_position_pct:.1f}% of portfolio). Target < 15–20% per position and add additional holdings for smoother exposure."
        )

    if n_holdings < 5:
        recommendations.append(
            f"Increase the number of holdings (currently {n_holdings}). Diversification improves materially when you move toward 8–15 positions."
        )

    if hhi >= 0.25:
        recommendations.append(
            f"Concentration remains high (HHI={hhi:.3f}). Consider spreading capital across more names and sectors to reduce single-name risk."
        )

    # Sector-based guidance
    if sector_allocation_pct:
        dominant_sector, dominant_sector_pct = max(sector_allocation_pct.items(), key=lambda kv: kv[1])
        if dominant_sector_pct >= 50.0:
            recommendations.append(
                f"Sector exposure is dominated by '{dominant_sector}' ({dominant_sector_pct:.1f}%). Add exposure to other sectors to reduce sector-driven drawdowns."
            )

        if len(sector_allocation_pct) <= 2:
            recommendations.append(
                "Broaden sector coverage. Aim for at least 3–5 sectors with meaningful allocations."
            )

    if diversification_score >= 75.0:
        recommendations.append(
            "Diversification looks healthy. Maintain current allocation discipline and periodically rebalance if weights drift."
        )
    else:
        recommendations.append(
            "Practical approach: trim overweight positions, then reallocate into a mix of sectors you currently underweight (while keeping each new position below your concentration threshold)."
        )

    # De-duplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for r in recommendations:
        if r not in seen:
            out.append(r)
            seen.add(r)
    return out[:6]


async def analyze_diversification(
    *,
    portfolio_id: UUID,
    db: AsyncSession,
    current_user: Any,
    refresh_if_missing_prices: bool = True,
) -> dict[str, Any]:
    """Calculate diversification analytics from current portfolio holdings.

    Returns a JSON-compatible dict with:
      - sector_allocation: list of {sector, allocation_pct, current_value}
      - concentration_index_hhi: float
      - largest_position_pct: float
      - diversification_score: float (0–100)
      - recommendations: list[str]

    Metrics are computed using the latest available close_price per symbol.
    """

    await _get_user_portfolio(db=db, portfolio_id=portfolio_id, current_user=current_user)

    holdings = await _compute_holdings(
        db=db,
        portfolio_id=portfolio_id,
        refresh_if_missing_prices=refresh_if_missing_prices,
    )

    if not holdings:
        return {
            "sector_allocation": [],
            "concentration_index_hhi": 0.0,
            "largest_position_pct": 0.0,
            "diversification_score": 0.0,
            "recommendations": [
                "Portfolio is empty or has no positive market value holdings. Add holdings to generate diversification analytics."
            ],
        }

    total_value = float(sum(h.market_value for h in holdings))
    if total_value <= 0:
        return {
            "sector_allocation": [],
            "concentration_index_hhi": 0.0,
            "largest_position_pct": 0.0,
            "diversification_score": 0.0,
            "recommendations": [
                "Portfolio market value is non-positive. Diversification analytics require positive market value holdings."
            ],
        }

    weights = [h.market_value / total_value for h in holdings]
    hhi = _compute_hhi(weights)

    largest_holding = max(holdings, key=lambda h: h.market_value)
    largest_position_pct = _safe_pct(largest_holding.market_value, total_value)

    diversification_score = _diversification_score_from_hhi(hhi=hhi, n_holdings=len(holdings))

    # Sector allocation
    sector_values: dict[str, float] = {}
    for h in holdings:
        sector = h.sector or "Unknown"
        sector_values[sector] = sector_values.get(sector, 0.0) + h.market_value

    sector_allocation_pct: dict[str, float] = {
        s: _safe_pct(v, total_value) for s, v in sector_values.items()
    }

    sector_rows = [
        {
            "sector": sector,
            "allocation_pct": _round2(pct),
            "current_value": _round2(sector_values[sector]),
        }
        for sector, pct in sector_allocation_pct.items()
    ]
    sector_rows.sort(key=lambda r: r["current_value"], reverse=True)

    recommendations = _build_recommendations(
        holdings=holdings,
        sector_allocation_pct=sector_allocation_pct,
        largest_position_pct=largest_position_pct,
        hhi=hhi,
        diversification_score=diversification_score,
    )

    return {
        "sector_allocation": sector_rows,
        "concentration_index_hhi": _round2(hhi),
        "largest_position_pct": _round2(largest_position_pct),
        "diversification_score": _round2(diversification_score),
        "recommendations": recommendations,
    }


__all__ = ["analyze_diversification"]

