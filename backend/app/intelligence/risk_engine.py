from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.historical_price import HistoricalPrice
from app.models.market_symbol import MarketSymbol
from app.models.portfolio import Portfolio
from app.models.portfolio_transaction import PortfolioTransaction
from app.services.historical_price_service import HistoricalPriceService


# -------------------------
# Helpers
# -------------------------

def _round2(v: float) -> float:
    v2 = round(v, 2)
    return 0.0 if v2 == -0.0 else v2


def _safe_div(n: float, d: float) -> float:
    if d == 0:
        return 0.0
    return float(n / d)


def _pct_returns_from_prices(prices: list[float]) -> list[float]:
    """Simple returns r_t = P_t/P_{t-1}-1."""
    if len(prices) < 2:
        return []
    rets: list[float] = []
    prev = prices[0]
    for p in prices[1:]:
        if prev == 0:
            rets.append(0.0)
        else:
            rets.append((p / prev) - 1.0)
        prev = p
    return rets


def _sample_stdev(xs: list[float]) -> float:
    """Sample standard deviation (n-1)."""
    n = len(xs)
    if n < 2:
        return 0.0
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    return math.sqrt(var) if var > 0 else 0.0


def _annualize_vol(daily_vol: float, trading_days: int) -> float:
    # Annualized volatility ~ vol_daily * sqrt(N)
    return float(daily_vol * math.sqrt(trading_days))


def _max_drawdown_from_prices(prices: list[float]) -> float:
    """Maximum drawdown as a negative number (e.g., -0.25)."""
    if not prices:
        return 0.0
    peak = prices[0]
    max_dd = 0.0
    for p in prices[1:]:
        if p > peak:
            peak = p
        if peak == 0:
            continue
        dd = (p / peak) - 1.0
        if dd < max_dd:
            max_dd = dd
    return float(max_dd)


def _beta_from_series(asset_returns: list[float], market_returns: list[float]) -> Optional[float]:
    """Beta = Cov(asset, market) / Var(market) using sample statistics."""
    n = min(len(asset_returns), len(market_returns))
    if n < 2:
        return None
    a = asset_returns[-n:]
    m = market_returns[-n:]

    mean_a = sum(a) / n
    mean_m = sum(m) / n
    cov = sum((a[i] - mean_a) * (m[i] - mean_m) for i in range(n)) / (n - 1)
    var_m = sum((m[i] - mean_m) ** 2 for i in range(n)) / (n - 1)
    if var_m == 0:
        return None
    return float(cov / var_m)


def _sharpe_ratio(asset_returns: list[float], risk_free_rate_annual: float, trading_days: int) -> float:
    """Sharpe using daily returns. risk_free_rate_annual is an annual rate."""
    if len(asset_returns) < 2:
        return 0.0

    # Convert annual risk-free to daily equivalent.
    # For small rates, (1+r)^(1/N)-1 is typical.
    rf_daily = (1.0 + risk_free_rate_annual) ** (1.0 / trading_days) - 1.0
    excess = [r - rf_daily for r in asset_returns]
    mean_excess = sum(excess) / len(excess)
    vol = _sample_stdev(asset_returns)
    if vol == 0:
        return 0.0
    return float(mean_excess / vol)


def _sortino_ratio(asset_returns: list[float], risk_free_rate_annual: float, trading_days: int) -> float:
    """Sortino uses downside deviation relative to risk-free (daily)."""
    if len(asset_returns) < 2:
        return 0.0

    rf_daily = (1.0 + risk_free_rate_annual) ** (1.0 / trading_days) - 1.0
    downside = [(min(r - rf_daily, 0.0)) ** 2 for r in asset_returns]
    if not downside:
        return 0.0
    # Downside deviation uses sample sqrt of mean of squares below 0.
    # If all excess are >= 0, downside deviation is 0.
    dd = math.sqrt(sum(downside) / len(downside))
    if dd == 0:
        return 0.0

    mean_excess = (sum(r - rf_daily for r in asset_returns)) / len(asset_returns)
    return float(mean_excess / dd)


def _value_at_risk_95(returns: list[float]) -> float:
    """VaR at 95% = -quantile_5(return). Returns are simple returns.

    Output is a positive loss magnitude (e.g., 0.03 means -3% at 95% confidence).
    """
    if len(returns) < 2:
        return 0.0
    xs = sorted(returns)
    # quantile at 5th percentile
    k = int(math.floor(0.05 * (len(xs) - 1)))
    q = xs[k]
    return float(-q if q < 0 else 0.0)


def _risk_score_from_metrics(
    *,
    annualized_vol: float,
    max_drawdown: float,
    var_95: float,
    beta: Optional[float],
) -> int:
    """Heuristic risk score mapping to 0..100.

    - annualized_vol higher => higher risk
    - max_drawdown more negative => higher risk
    - var_95 higher => higher risk
    - beta (if available) higher => higher risk
    """

    # Normalize with soft caps.
    vol_n = min(1.0, annualized_vol / 0.40)  # 40% vol -> full
    dd_n = min(1.0, abs(max_drawdown) / 0.40)  # 40% drawdown -> full
    var_n = min(1.0, var_95 / 0.10)  # 10% daily VaR magnitude -> full
    beta_n = 0.0 if beta is None else min(1.0, abs(beta) / 2.0)

    # Weighted blend.
    score = 0.45 * vol_n + 0.35 * dd_n + 0.15 * var_n + 0.05 * beta_n
    return int(round(score * 100))


def _risk_level_from_score(score: int) -> str:
    if score >= 75:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


# -------------------------
# Data access + portfolio aggregation
# -------------------------


@dataclass(frozen=True)
class _Holding:
    symbol_id: UUID
    ticker: str
    quantity: float
    current_price: float
    market_value: float


async def _get_user_portfolio(*, db: AsyncSession, portfolio_id: UUID, current_user: Any) -> Portfolio:
    current_user_id = getattr(current_user, "id", None)
    if current_user_id is None:
        raise PermissionError("Unauthorized")

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
        raise LookupError("Portfolio not found")
    return portfolio


async def _get_portfolio_symbol_quantities(*, db: AsyncSession, portfolio_id: UUID) -> list[tuple[UUID, str, float]]:
    """Net quantity by symbol from portfolio transactions."""
    t = PortfolioTransaction

    quantity_signed = func.sum(func.case((t.transaction_type == "SELL", -t.quantity), else_=t.quantity))

    stmt = (
        select(MarketSymbol.id, MarketSymbol.ticker, quantity_signed.label("net_quantity"))
        .join_from(t, MarketSymbol, t.symbol_id == MarketSymbol.id)
        .where(t.portfolio_id == portfolio_id)
        .group_by(MarketSymbol.id, MarketSymbol.ticker)
        .having(quantity_signed != 0)
    )

    res = await db.execute(stmt)
    rows = res.all()
    return [(row.id, row.ticker, float(row.net_quantity)) for row in rows]


async def _ensure_latest_prices_for_symbols(
    *,
    db: AsyncSession,
    symbols: list[tuple[UUID, str]],
    refresh_if_missing: bool,
) -> dict[UUID, float]:
    """Fetch latest close_price per symbol_id; optionally refresh missing."""
    if not symbols:
        return {}

    symbol_ids = [s[0] for s in symbols]
    tickers = [s[1] for s in symbols]

    max_stmt = (
        select(HistoricalPrice.symbol_id, func.max(HistoricalPrice.as_of).label("as_of"))
        .where(HistoricalPrice.symbol_id.in_(symbol_ids))
        .group_by(HistoricalPrice.symbol_id)
    )
    asof_res = await db.execute(max_stmt)
    asof_rows = asof_res.all()
    asof_map: dict[UUID, Any] = {r.symbol_id: r.as_of for r in asof_rows}

    price_map: dict[UUID, float] = {}
    missing: list[tuple[UUID, str]] = []
    for sid, ticker in zip(symbol_ids, tickers):
        as_of = asof_map.get(sid)
        if as_of is None:
            missing.append((sid, ticker))
            continue
        price_res = await db.execute(
            select(HistoricalPrice.close_price).where(HistoricalPrice.symbol_id == sid, HistoricalPrice.as_of == as_of)
        )
        price = price_res.scalar_one_or_none()
        if price is None:
            missing.append((sid, ticker))
            continue
        price_map[sid] = float(price)

    if missing and refresh_if_missing:
        req = None
        # Import lazily to avoid unused import if risk engine is used without refresh.
        from app.schemas.historical_price import HistoricalPriceRefreshRequest

        req = HistoricalPriceRefreshRequest(period="daily")
        for sid, ticker in missing:
            await HistoricalPriceService.refresh_symbol(db, current_symbol_id=sid, ticker=ticker, req=req)

        # Re-run query for missing
        asof_res2 = await db.execute(max_stmt)
        asof_rows2 = asof_res2.all()
        asof_map2: dict[UUID, Any] = {r.symbol_id: r.as_of for r in asof_rows2}
        for sid, ticker in missing:
            as_of = asof_map2.get(sid)
            if as_of is None:
                continue
            price_res2 = await db.execute(
                select(HistoricalPrice.close_price).where(HistoricalPrice.symbol_id == sid, HistoricalPrice.as_of == as_of)
            )
            price2 = price_res2.scalar_one_or_none()
            if price2 is not None:
                price_map[sid] = float(price2)

    return price_map


async def _get_portfolio_holdings_current(*, db: AsyncSession, portfolio_id: UUID, refresh_if_missing: bool) -> list[_Holding]:
    qtys = await _get_portfolio_symbol_quantities(db=db, portfolio_id=portfolio_id)
    if not qtys:
        return []

    symbol_pairs = [(sid, ticker) for sid, ticker, _q in qtys]
    prices = await _ensure_latest_prices_for_symbols(db=db, symbols=symbol_pairs, refresh_if_missing=refresh_if_missing)

    holdings: list[_Holding] = []
    for sid, ticker, qty in qtys:
        p = prices.get(sid)
        if p is None:
            continue
        holdings.append(_Holding(symbol_id=sid, ticker=ticker, quantity=qty, current_price=p, market_value=qty * p))
    return holdings


async def _get_price_matrix_aligned_days(
    *,
    db: AsyncSession,
    symbol_ids: list[UUID],
    start_date: datetime,
    end_date: datetime,
) -> dict[UUID, list[float]]:
    """Fetch close prices for each symbol within [start_date, end_date], ordered ascending by as_of."""
    if not symbol_ids:
        return {}

    stmt = (
        select(HistoricalPrice.symbol_id, HistoricalPrice.as_of, HistoricalPrice.close_price)
        .where(HistoricalPrice.symbol_id.in_(symbol_ids))
        .where(HistoricalPrice.as_of >= start_date)
        .where(HistoricalPrice.as_of <= end_date)
        .order_by(HistoricalPrice.as_of.asc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    # Collect series per symbol.
    series: dict[UUID, list[tuple[datetime, float]]] = {sid: [] for sid in symbol_ids}
    for sid, as_of, close_price in rows:
        series.setdefault(sid, []).append((as_of, float(close_price)))

    # Convert to close-only lists, but we will align by intersection of dates.
    dates_per_symbol: dict[UUID, list[datetime]] = {sid: [t[0] for t in series[sid]] for sid in symbol_ids}

    common_dates: Optional[set[datetime]] = None
    for sid in symbol_ids:
        dset = set(dates_per_symbol.get(sid, []))
        common_dates = dset if common_dates is None else (common_dates & dset)

    if not common_dates:
        return {sid: [] for sid in symbol_ids}

    sorted_common = sorted(common_dates)

    out: dict[UUID, list[float]] = {}
    for sid in symbol_ids:
        # Map date -> close
        m = {dt: close for (dt, close) in series.get(sid, [])}
        out[sid] = [m[dt] for dt in sorted_common if dt in m]

    return out


# -------------------------
# Public API
# -------------------------


async def calculate_portfolio_risk(
    *,
    portfolio_id: UUID,
    db: AsyncSession,
    current_user: Any,
    lookback_days: int = 252,
    trading_days_per_year: int = 252,
    risk_free_rate_annual: float = 0.0,
    market_index_ticker: str = "SPY",
    refresh_if_missing_prices: bool = False,
) -> dict[str, Any]:
    """Compute portfolio risk metrics from historical close prices.

    Returned dict:
      {
        risk_score,
        risk_level,
        metrics: {
          portfolio_volatility,
          annualized_volatility,
          maximum_drawdown,
          beta,
          sharpe_ratio,
          sortino_ratio,
          value_at_risk_95
        }
      }

    Notes / assumptions:
      - Portfolio return series is computed using fixed share quantities and aligned daily close prices.
      - Portfolio prices are modeled as portfolio_value_t = sum_i (qty_i * close_i_t).
      - Beta uses a market index ticker (default SPY) if present with enough aligned history.
      - Sharpe/Sortino use risk_free_rate_annual; default 0.
    """

    # Validate portfolio ownership (keeps module consistent with rest of codebase style).
    await _get_user_portfolio(db=db, portfolio_id=portfolio_id, current_user=current_user)

    holdings = await _get_portfolio_holdings_current(
        db=db,
        portfolio_id=portfolio_id,
        refresh_if_missing=refresh_if_missing_prices,
    )

    if not holdings:
        metrics = {
            "portfolio_volatility": 0.0,
            "annualized_volatility": 0.0,
            "maximum_drawdown": 0.0,
            "beta": None,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "value_at_risk_95": 0.0,
        }
        return {"risk_score": 0, "risk_level": "Low", "metrics": metrics}

    # Time window.
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=int(lookback_days * 1.5))
    # We'll still align/intersect to the actual common trading days present.

    symbol_ids = [h.symbol_id for h in holdings]

    # Portfolio value series from aligned prices.
    price_matrix = await _get_price_matrix_aligned_days(
        db=db,
        symbol_ids=symbol_ids,
        start_date=start_date,
        end_date=end_date,
    )

    # Align lengths.
    series_lengths = [len(price_matrix.get(sid, [])) for sid in symbol_ids]
    n = min(series_lengths) if series_lengths else 0

    if n < 2:
        metrics = {
            "portfolio_volatility": 0.0,
            "annualized_volatility": 0.0,
            "maximum_drawdown": 0.0,
            "beta": None,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "value_at_risk_95": 0.0,
        }
        return {"risk_score": 0, "risk_level": "Low", "metrics": metrics}

    # Compute portfolio value series as weighted by fixed share quantities.
    portfolio_values: list[float] = []
    for t in range(n):
        v = 0.0
        for h in holdings:
            closes = price_matrix.get(h.symbol_id, [])
            if t >= len(closes):
                continue
            v += h.quantity * closes[t]
        portfolio_values.append(float(v))

    # Returns
    portfolio_returns = _pct_returns_from_prices(portfolio_values)

    daily_vol = _sample_stdev(portfolio_returns)
    annualized_vol = _annualize_vol(daily_vol, trading_days_per_year)

    max_drawdown = _max_drawdown_from_prices(portfolio_values)

    sharpe = _sharpe_ratio(portfolio_returns, risk_free_rate_annual=risk_free_rate_annual, trading_days=trading_days_per_year)
    sortino = _sortino_ratio(portfolio_returns, risk_free_rate_annual=risk_free_rate_annual, trading_days=trading_days_per_year)
    var_95 = _value_at_risk_95(portfolio_returns)

    # Beta
    beta: Optional[float] = None
    # Find market symbol.
    market_ticker_norm = market_index_ticker.strip().upper()
    market_res = await db.execute(select(MarketSymbol.id).where(MarketSymbol.ticker == market_ticker_norm).limit(1))
    market_symbol_id = market_res.scalar_one_or_none()

    if market_symbol_id is not None:
        market_prices_series = await _get_price_matrix_aligned_days(
            db=db,
            symbol_ids=[market_symbol_id],
            start_date=start_date,
            end_date=end_date,
        )
        market_prices = market_prices_series.get(market_symbol_id, [])
        if len(market_prices) >= 2:
            # Align with portfolio returns by truncating to common length on returns.
            m_rets = _pct_returns_from_prices(market_prices)
            k = min(len(portfolio_returns), len(m_rets))
            if k >= 2:
                beta = _beta_from_series(portfolio_returns[-k:], m_rets[-k:])

    risk_score = _risk_score_from_metrics(
        annualized_vol=annualized_vol,
        max_drawdown=max_drawdown,
        var_95=var_95,
        beta=beta,
    )
    risk_level = _risk_level_from_score(risk_score)

    metrics_out = {
        "portfolio_volatility": _round2(daily_vol),
        "annualized_volatility": _round2(annualized_vol),
        "maximum_drawdown": _round2(max_drawdown),
        "beta": None if beta is None else _round2(beta),
        "sharpe_ratio": _round2(sharpe),
        "sortino_ratio": _round2(sortino),
        "value_at_risk_95": _round2(var_95),
    }

    return {"risk_score": risk_score, "risk_level": risk_level, "metrics": metrics_out}

