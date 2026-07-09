from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_access_token
from app.database.session import get_db
from app.models import User
from app.services.user_service import UserService

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Resolve the currently authenticated user from a bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or not credentials.scheme.lower() == "bearer":
        raise credentials_exception

    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")
        if subject is None or payload.get("type") != "access":
            raise credentials_exception
    except ValueError as exc:
        raise credentials_exception from exc

    user = await UserService.get_user_by_id(db, subject)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Ensure the authenticated user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


def require_roles(*roles: str):
    """Build a role-based authorization dependency."""

    async def dependency(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if not current_user.role_assignments:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        assigned_roles = {assignment.role.name for assignment in current_user.role_assignments}
        if not set(roles).issubset(assigned_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency
