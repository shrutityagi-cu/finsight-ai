from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import HistoricalPrice, MarketSymbol, Portfolio, PortfolioTransaction
from app.services.portfolio_analytics_service import PortfolioIntelligenceService


@pytest.mark.asyncio
async def test_missing_default_portfolio_404(db_session):
    # db_session fixture should provide an authenticated-like user id; for this unit test we just pass a UUID.
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    svc = PortfolioIntelligenceService(db=db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.get_summary(current_user_id=user_id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_empty_default_portfolio_returns_zeros(db_session, create_user_with_default_portfolio):
    current_user, portfolio = create_user_with_default_portfolio

    svc = PortfolioIntelligenceService(db=db_session)
    summary = await svc.get_summary(current_user_id=current_user.id)
    assert summary["number_of_holdings"] == 0
    assert summary["total_portfolio_value"] == 0.0


@pytest.mark.asyncio
async def test_one_holding_gain_loss_and_allocation(db_session, create_user_with_default_portfolio):
    current_user, portfolio = create_user_with_default_portfolio

    sym = MarketSymbol(ticker="AAPL", name="Apple", sector="Technology", industry="Consumer Electronics", currency="USD")
    db_session.add(sym)
    await db_session.flush()

    # Buy 10 shares at $100 with $0 fees
    t0 = datetime.now(timezone.utc) - timedelta(days=10)
    tx = PortfolioTransaction(
        portfolio_id=portfolio.id,
        symbol_id=sym.id,
        transaction_type="BUY",
        quantity=10.0,
        unit_price=100.0,
        fees=0.0,
        currency="USD",
        executed_at=t0,
    )
    db_session.add(tx)

    # Latest close $120
    hp = HistoricalPrice(
        symbol_id=sym.id,
        as_of=datetime.now(timezone.utc) - timedelta(days=1),
        open_price=115.0,
        high_price=121.0,
        low_price=114.0,
        close_price=120.0,
        volume=1000,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(hp)
    await db_session.commit()

    svc = PortfolioIntelligenceService(db=db_session)
    holdings = await svc.get_holdings(current_user_id=current_user.id)
    assert len(holdings) == 1
    h = holdings[0]

    assert h["ticker"] == "AAPL"
    assert h["quantity"] == 10.0
    assert h["average_buy_price"] == 100.0
    assert h["current_price"] == 120.0
    assert h["market_value"] == 1200.0
    assert h["cost_basis"] == 1000.0
    assert h["profit_loss"] == 200.0

    allocation = await svc.get_asset_allocation(current_user_id=current_user.id)
    assert len(allocation) == 1
    assert allocation[0]["weight"] == 100.0


@pytest.mark.asyncio
async def test_missing_historical_price_raises_503(db_session, create_user_with_default_portfolio):
    current_user, portfolio = create_user_with_default_portfolio

    sym = MarketSymbol(ticker="MSFT", name="Microsoft", sector="Technology", industry="Software", currency="USD")
    db_session.add(sym)
    await db_session.flush()

    tx = PortfolioTransaction(
        portfolio_id=portfolio.id,
        symbol_id=sym.id,
        transaction_type="BUY",
        quantity=5.0,
        unit_price=200.0,
        fees=0.0,
        currency="USD",
        executed_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    db_session.add(tx)
    await db_session.commit()

    svc = PortfolioIntelligenceService(db=db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.get_holdings(current_user_id=current_user.id)
    assert exc.value.status_code == 503

