from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.core.security import generate_password_hash, verify_password


class UserService:
    """Service layer for user-related persistence and lookup operations."""

    @staticmethod
    async def create_user(db: AsyncSession, *, email: str, username: str, password: str, full_name: str | None = None) -> User:
        user = User(
            email=email,
            username=username,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str | UUID) -> Optional[User]:
        normalized_id = str(user_id)
        result = await db.execute(select(User))
        for candidate in result.scalars().all():
            if str(candidate.id) == normalized_id:
                return candidate
        return None

    @staticmethod
    async def authenticate_user(db: AsyncSession, *, email_or_username: str, password: str) -> Optional[User]:
        user = await UserService.get_user_by_email(db, email_or_username)
        if user is None:
            user = await UserService.get_user_by_username(db, email_or_username)
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user
