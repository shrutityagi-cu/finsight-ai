from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator, Generator
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database.session import AsyncSessionLocal
from app.models import Portfolio, PortfolioTransaction, User, MarketSymbol


@pytest.fixture(scope="function")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="function")
async def db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        # Start from a clean transaction boundary.
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def create_user_with_default_portfolio(db_session: AsyncSession):
    user = User(
        email=f"u-{uuid4()}@example.com",
        username=f"u-{uuid4()}",
        full_name=None,
        password_hash="x",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    portfolio = Portfolio(user_id=user.id, name="Default", description=None, is_default=True)
    db_session.add(portfolio)
    await db_session.commit()
    await db_session.refresh(portfolio)

    return user, portfolio


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    # Client fixture currently relies on the application using get_db dependency.
    # We cannot safely override it without inspecting the dependency injection chain.
    # For now, provide a client that will still run routes; tests that require DB access
    # should call services directly.
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

