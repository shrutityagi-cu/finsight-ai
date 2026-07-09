from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models import HistoricalPrice, MarketSymbol, PortfolioTransaction


@pytest.mark.asyncio
async def test_dashboard_endpoints_status(client: AsyncClient, db_session, create_user_with_default_portfolio):

    current_user, portfolio = create_user_with_default_portfolio

    sym = MarketSymbol(ticker="AAPL", name="Apple", sector="Technology", industry="Consumer Electronics", currency="USD")
    db_session.add(sym)
    await db_session.flush()

    tx = PortfolioTransaction(
        portfolio_id=portfolio.id,
        symbol_id=sym.id,
        transaction_type="BUY",
        quantity=1.0,
        unit_price=100.0,
        fees=0.0,
        currency="USD",
        executed_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    db_session.add(tx)

    hp = HistoricalPrice(
        symbol_id=sym.id,
        as_of=datetime.now(timezone.utc) - timedelta(days=1),
        open_price=95.0,
        high_price=110.0,
        low_price=90.0,
        close_price=105.0,
        volume=1000,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(hp)
    await db_session.commit()

    # Auth + user scoping is handled by the existing test client fixture.
    resp = await client.get("/api/v1/portfolio-intelligence")
    assert resp.status_code in (404, 405)  # route base should not exist

    resp = await client.get("/api/v1/portfolio-intelligence/summary")
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert "total_portfolio_value" in body

    resp = await client.get("/api/v1/portfolio-intelligence/allocation")
    assert resp.status_code == status.HTTP_200_OK
    alloc = resp.json()
    assert isinstance(alloc, list)
    assert len(alloc) == 1

