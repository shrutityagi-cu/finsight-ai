from __future__ import annotations

import math
from typing import Iterable, Optional, Sequence


Number = float


def _validate_non_empty_series(values: Sequence[Number], *, name: str) -> None:
    if len(values) == 0:
        raise ValueError(f"{name} must be a non-empty sequence")


def _to_list(values: Iterable[Number]) -> list[Number]:
    return [float(v) for v in values]


def _sample_stdev(values: Sequence[Number]) -> float:
    """Sample standard deviation (ddof=1)."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    return math.sqrt(var) if var > 0 else 0.0


def _safe_div(n: Number, d: Number) -> float:
    return 0.0 if d == 0 else float(n / d)


def _pct_returns_from_prices(prices: Sequence[Number]) -> list[float]:
    """Simple returns: r_t = P_t/P_{t-1} - 1."""
    if len(prices) < 2:
        return []
    out: list[float] = []
    prev = float(prices[0])
    for p in prices[1:]:
        p = float(p)
        if prev == 0:
            out.append(0.0)
        else:
            out.append((p / prev) - 1.0)
        prev = p
    return out


def calculate_compound_return(start_value: Number, end_value: Number) -> float:
    """Compound return (simple total return)."""
    start_value = float(start_value)
    end_value = float(end_value)
    if start_value == 0:
        return 0.0
    return float((end_value / start_value) - 1.0)


def calculate_cagr(*, start_value: Number, end_value: Number, years: Number) -> float:
    """Calculate Compound Annual Growth Rate (CAGR).

    Args:
        start_value: Starting value (>0 recommended).
        end_value: Ending value.
        years: Number of years (must be > 0).

    Returns:
        CAGR as a decimal fraction (e.g., 0.12 for 12%/year). Returns 0.0 if
        inputs are not sufficient or CAGR is not computable.
    """
    start_value = float(start_value)
    end_value = float(end_value)
    years = float(years)

    if years <= 0:
        raise ValueError("years must be > 0")
    if start_value == 0:
        return 0.0

    # If end_value < 0, CAGR is not real-valued. Return 0.0 for robustness.
    if end_value < 0:
        return 0.0

    return float((end_value / start_value) ** (1.0 / years) - 1.0)


def calculate_return(prices: Iterable[Number]) -> float:
    """Calculate total return over a price/value series.

    Uses simple total return: end/start - 1.

    Args:
        prices: Sequence of values (prices, portfolio values, etc.).

    Returns:
        Total return as a decimal fraction.
    """
    vals = _to_list(prices)
    _validate_non_empty_series(vals, name="prices")
    if len(vals) == 1:
        return 0.0
    start = vals[0]
    end = vals[-1]
    return calculate_compound_return(start_value=start, end_value=end)


def calculate_roi(*, start_value: Number, end_value: Number) -> float:
    """Return on Investment (ROI).

    ROI is the same as total return: (end - start)/start.

    Returns 0.0 if start_value is 0.
    """
    start_value = float(start_value)
    end_value = float(end_value)
    if start_value == 0:
        return 0.0
    return float((end_value - start_value) / start_value)


def calculate_volatility(returns: Iterable[Number], *, trading_days_per_year: int = 252) -> float:
    """Annualized volatility from a returns series.

    Args:
        returns: Sequence of simple returns (r_t).
        trading_days_per_year: Annualization factor.

    Returns:
        Annualized volatility (standard deviation) as a decimal fraction.
    """
    rs = _to_list(returns)
    if len(rs) < 2:
        return 0.0
    daily_vol = _sample_stdev(rs)
    return float(daily_vol * math.sqrt(float(trading_days_per_year)))


def calculate_drawdown(prices: Iterable[Number]) -> float:
    """Maximum drawdown as a negative number.

    Drawdown at time t: P_t/peak - 1. Output is the most negative drawdown.

    Returns:
        0.0 if the series is empty or not computable.
    """
    vals = _to_list(prices)
    if not vals:
        return 0.0

    peak = vals[0]
    max_dd = 0.0
    for p in vals[1:]:
        if p > peak:
            peak = p
        if peak == 0:
            continue
        dd = (p / peak) - 1.0
        if dd < max_dd:
            max_dd = dd
    return float(max_dd)


def calculate_beta(
    *,
    asset_returns: Sequence[Number],
    market_returns: Sequence[Number],
) -> Optional[float]:
    """Calculate beta of an asset relative to a market benchmark.

    Beta = Cov(asset, market)/Var(market) using sample statistics (ddof=1).

    Returns:
        Beta as float, or None if insufficient data or market variance is 0.
    """
    a = _to_list(asset_returns)
    m = _to_list(market_returns)
    n = min(len(a), len(m))
    if n < 2:
        return None

    a2 = a[-n:]
    m2 = m[-n:]

    mean_a = sum(a2) / n
    mean_m = sum(m2) / n

    cov = sum((a2[i] - mean_a) * (m2[i] - mean_m) for i in range(n)) / (n - 1)
    var_m = sum((m2[i] - mean_m) ** 2 for i in range(n)) / (n - 1)
    if var_m == 0:
        return None
    return float(cov / var_m)


def calculate_alpha(
    *,
    asset_returns: Sequence[Number],
    market_returns: Sequence[Number],
    risk_free_rate_annual: Number = 0.0,
    trading_days_per_year: int = 252,
) -> float:
    """Estimate alpha using a simplified CAPM regression.

    This computes:
      alpha = (mean_asset - rf_daily) - beta * (mean_market - rf_daily)

    where all means are computed on daily returns.

    Returns:
        Alpha in daily-return terms. (If you want annualized alpha, multiply
        by trading_days_per_year approximately.)

    Notes:
        - This is not a full OLS regression intercept; it is a CAPM-style
          estimate using beta from covariance/variance.
        - Returns 0.0 when not computable.
    """
    a = _to_list(asset_returns)
    m = _to_list(market_returns)
    n = min(len(a), len(m))
    if n < 2:
        return 0.0

    a2 = a[-n:]
    m2 = m[-n:]

    rf_annual = float(risk_free_rate_annual)
    rf_daily = (1.0 + rf_annual) ** (1.0 / float(trading_days_per_year)) - 1.0

    mean_a = sum(a2) / n
    mean_m = sum(m2) / n

    beta = calculate_beta(asset_returns=a2, market_returns=m2)
    if beta is None:
        return 0.0

    alpha_daily = (mean_a - rf_daily) - beta * (mean_m - rf_daily)
    return float(alpha_daily)


def calculate_sharpe(
    returns: Sequence[Number],
    *,
    risk_free_rate_annual: Number = 0.0,
    trading_days_per_year: int = 252,
) -> float:
    """Calculate Sharpe ratio using daily returns.

    Sharpe = mean(excess_returns)/std(returns), annualization is handled by
    using risk-free conversion only; volatility is standard deviation of the
    provided daily returns.

    Args:
        returns: Sequence of simple returns.
        risk_free_rate_annual: Annual risk-free rate as decimal.

    Returns:
        Sharpe ratio (dimensionless). Returns 0.0 if not computable.
    """
    rs = _to_list(returns)
    if len(rs) < 2:
        return 0.0

    rf_annual = float(risk_free_rate_annual)
    rf_daily = (1.0 + rf_annual) ** (1.0 / float(trading_days_per_year)) - 1.0

    excess = [r - rf_daily for r in rs]
    mean_excess = sum(excess) / len(excess)
    vol = _sample_stdev(rs)
    if vol == 0:
        return 0.0

    return float(mean_excess / vol)


def calculate_sortino(
    returns: Sequence[Number],
    *,
    risk_free_rate_annual: Number = 0.0,
    trading_days_per_year: int = 252,
) -> float:
    """Calculate Sortino ratio using downside deviation.

    Sortino = mean(excess_returns)/downside_deviation, where downside is
    computed against the daily risk-free rate.

    Returns 0.0 when downside deviation is 0 or insufficient data.
    """
    rs = _to_list(returns)
    if len(rs) < 2:
        return 0.0

    rf_annual = float(risk_free_rate_annual)
    rf_daily = (1.0 + rf_annual) ** (1.0 / float(trading_days_per_year)) - 1.0

    downside_sq = [(min(r - rf_daily, 0.0)) ** 2 for r in rs]
    if not downside_sq:
        return 0.0

    dd = math.sqrt(sum(downside_sq) / len(downside_sq))
    if dd == 0:
        return 0.0

    mean_excess = (sum(r - rf_daily for r in rs)) / len(rs)
    return float(mean_excess / dd)


__all__ = [

    "calculate_cagr",
    "calculate_return",
    "calculate_roi",
    "calculate_volatility",
    "calculate_compound_return",
    "calculate_drawdown",
    "calculate_beta",
    "calculate_alpha",
    "calculate_sharpe",
    "calculate_sortino",
]

