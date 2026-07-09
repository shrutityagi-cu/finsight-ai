from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import create_access_token, decode_access_token
from app.core.security import generate_password_hash, verify_password
from app.models import Base
from app.schemas.auth import LoginRequest, RefreshTokenRequest
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def test_password_hashing_and_verification() -> None:
    hashed_password = generate_password_hash("super-secret")

    assert verify_password("super-secret", hashed_password)
    assert not verify_password("wrong-password", hashed_password)


def test_jwt_round_trip() -> None:
    subject = str(uuid4())
    token = create_access_token({"sub": subject, "type": "access"})

    payload = decode_access_token(token)

    assert payload["sub"] == subject
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_registration_and_login_flow(db_session: AsyncSession) -> None:
    auth_service = AuthService()

    registered = await auth_service.register_user(
        db_session,
        UserCreate(
            email="test@example.com",
            username="tester",
            password="super-secret",
            full_name="Test User",
        ),
    )

    assert registered.access_token
    assert registered.refresh_token

    login_result = await auth_service.login_user(
        db_session,
        LoginRequest(email_or_username="tester", password="super-secret"),
    )

    assert login_result.access_token
    assert login_result.refresh_token

    refreshed = await auth_service.refresh_access_token(
        db_session,
        RefreshTokenRequest(refresh_token=login_result.refresh_token),
    )

    assert refreshed.access_token
    assert refreshed.refresh_token
