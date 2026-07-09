from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, create_refresh_token, decode_access_token
from app.core.security import generate_password_hash, verify_password
from app.models import RefreshToken, User
from app.schemas.auth import AuthenticatedUserResponse, TokenResponse
from app.schemas.user import UserCreate
from app.services.user_service import UserService


class AuthService:
    """Service layer implementing authentication, token issuance, and rotation."""

    @staticmethod
    async def register_user(db: AsyncSession, user_in: UserCreate) -> TokenResponse:
        if await UserService.get_user_by_email(db, str(user_in.email)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        if await UserService.get_user_by_username(db, user_in.username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

        user = await UserService.create_user(
            db,
            email=str(user_in.email),
            username=user_in.username,
            password=user_in.password,
            full_name=user_in.full_name,
        )
        return await AuthService._issue_tokens(db, user)

    @staticmethod
    async def login_user(db: AsyncSession, login_in: object) -> TokenResponse:
        user = await UserService.authenticate_user(
            db,
            email_or_username=login_in.email_or_username,
            password=login_in.password,
        )
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        return await AuthService._issue_tokens(db, user)

    @staticmethod
    async def refresh_access_token(db: AsyncSession, refresh_in: object) -> TokenResponse:
        try:
            payload = decode_access_token(refresh_in.refresh_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user = await UserService.get_user_by_id(db, user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        result = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))
        stored_tokens = result.scalars().all()
        if not stored_tokens:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        matched_token = None
        for token_record in stored_tokens:
            if not token_record.revoked_at and verify_password(refresh_in.refresh_token, token_record.token_hash):
                matched_token = token_record
                break

        if matched_token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        matched_token.revoked_at = datetime.now(timezone.utc)
        matched_token.replaced_by_token_hash = generate_password_hash(refresh_in.refresh_token)
        await db.flush()
        return await AuthService._issue_tokens(db, user)

    @staticmethod
    async def logout_user(db: AsyncSession, user: User, refresh_token: str | None = None) -> None:
        result = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))
        tokens = result.scalars().all()
        if refresh_token:
            for record in tokens:
                if not record.revoked_at and verify_password(refresh_token, record.token_hash):
                    record.revoked_at = datetime.now(timezone.utc)
                    break
        else:
            for record in tokens:
                if not record.revoked_at:
                    record.revoked_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def get_current_user_profile(user: User) -> AuthenticatedUserResponse:
        return AuthenticatedUserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
        )

    @staticmethod
    async def _issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
        access_token = create_access_token({"sub": str(user.id), "type": "access"})
        refresh_token_value = create_refresh_token({"sub": str(user.id), "type": "refresh"})
        refresh_hash = generate_password_hash(refresh_token_value)
        refresh_record = RefreshToken(
            id=uuid4(),
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            created_at=datetime.now(timezone.utc),
        )
        db.add(refresh_record)
        await db.commit()
        await db.refresh(refresh_record)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token_value)
