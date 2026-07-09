from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MarketSymbol, User, Watchlist, WatchlistItem
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistUpdate,
)

logger = logging.getLogger(__name__)


class WatchlistService:
    """Watchlist business logic.

    Ownership validation is enforced by always filtering via:
    `Watchlist.user_id == current_user.id`.
    """

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.strip()

    @staticmethod
    async def _get_owned_watchlist(
        db: AsyncSession, *, current_user: User, watchlist_id: UUID
    ) -> Optional[Watchlist]:
        stmt = (
            select(Watchlist)
            .where(
                Watchlist.id == watchlist_id,
                Watchlist.user_id == current_user.id,
                Watchlist.deleted_at.is_(None),
            )
            .limit(1)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def _get_watchlist_any_owner(
        db: AsyncSession, *, watchlist_id: UUID
    ) -> Optional[Watchlist]:
        stmt = (
            select(Watchlist)
            .where(Watchlist.id == watchlist_id, Watchlist.deleted_at.is_(None))
            .limit(1)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def _ensure_symbol_exists(db: AsyncSession, *, symbol_id: UUID) -> None:
        stmt = select(MarketSymbol).where(MarketSymbol.id == symbol_id).limit(1)
        res = await db.execute(stmt)
        if res.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="MarketSymbol not found")

    @staticmethod
    async def create_watchlist(
        db: AsyncSession, *, current_user: User, watchlist_in: WatchlistCreate
    ) -> Watchlist:
        """Create a new watchlist for the authenticated user."""
        name = WatchlistService._normalize_name(watchlist_in.name)
        if not name:
            raise HTTPException(status_code=400, detail="Watchlist name is required")

        dup_stmt = (
            select(Watchlist)
            .where(
                Watchlist.user_id == current_user.id,
                Watchlist.name == name,
                Watchlist.deleted_at.is_(None),
            )
            .limit(1)
        )
        dup_res = await db.execute(dup_stmt)
        if dup_res.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Watchlist name already exists")

        wl = Watchlist(user_id=current_user.id, name=name)
        db.add(wl)
        await db.commit()
        await db.refresh(wl)
        logger.info("Created watchlist id=%s for user_id=%s", wl.id, current_user.id)
        return wl

    @staticmethod
    async def list_watchlists(
        db: AsyncSession, *, current_user: User
    ) -> list[Watchlist]:
        """List all active watchlists owned by the authenticated user."""
        stmt = (
            select(Watchlist)
            .where(Watchlist.user_id == current_user.id, Watchlist.deleted_at.is_(None))
            .order_by(Watchlist.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_watchlist(
        db: AsyncSession, *, current_user: User, watchlist_id: UUID
    ) -> Watchlist:
        """Get a single watchlist by id, enforcing ownership."""
        wl_owned = await WatchlistService._get_owned_watchlist(
            db, current_user=current_user, watchlist_id=watchlist_id
        )
        if wl_owned is not None:
            return wl_owned

        wl_any = await WatchlistService._get_watchlist_any_owner(db, watchlist_id=watchlist_id)
        if wl_any is None:
            raise HTTPException(status_code=404, detail="Watchlist not found")

        # Exists but belongs to another user.
        raise HTTPException(status_code=403, detail="Forbidden")

    @staticmethod
    async def update_watchlist(
        db: AsyncSession,
        *,
        current_user: User,
        watchlist_id: UUID,
        watchlist_in: WatchlistUpdate,
    ) -> Watchlist:
        """Update a watchlist owned by the authenticated user."""
        wl = await WatchlistService.get_watchlist(
            db, current_user=current_user, watchlist_id=watchlist_id
        )

        if watchlist_in.name is not None:
            name = WatchlistService._normalize_name(watchlist_in.name)
            if not name:
                raise HTTPException(status_code=400, detail="Watchlist name is required")

            dup_stmt = (
                select(Watchlist)
                .where(
                    Watchlist.user_id == current_user.id,
                    Watchlist.name == name,
                    Watchlist.deleted_at.is_(None),
                    Watchlist.id != watchlist_id,
                )
                .limit(1)
            )
            dup_res = await db.execute(dup_stmt)
            if dup_res.scalar_one_or_none() is not None:
                raise HTTPException(status_code=409, detail="Watchlist name already exists")

            wl.name = name

        await db.commit()
        await db.refresh(wl)
        return wl

    @staticmethod
    async def delete_watchlist(
        db: AsyncSession, *, current_user: User, watchlist_id: UUID
    ) -> None:
        """Soft delete a watchlist owned by the authenticated user."""
        wl = await WatchlistService.get_watchlist(
            db, current_user=current_user, watchlist_id=watchlist_id
        )

        # Soft delete (Watchlist supports SoftDeleteMixin)
        wl.deleted_at = datetime.utcnow()
        await db.flush()
        await db.commit()

    @staticmethod
    async def list_items(
        db: AsyncSession, *, current_user: User, watchlist_id: UUID
    ) -> list[WatchlistItem]:
        """List items within a watchlist owned by the authenticated user."""
        await WatchlistService.get_watchlist(
            db, current_user=current_user, watchlist_id=watchlist_id
        )

        stmt = (
            select(WatchlistItem)
            .where(WatchlistItem.watchlist_id == watchlist_id)
            .order_by(WatchlistItem.added_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def add_item(
        db: AsyncSession,
        *,
        current_user: User,
        watchlist_id: UUID,
        item_in: WatchlistItemCreate,
    ) -> WatchlistItem:
        """Add an item to a watchlist, preventing duplicate symbols."""
        wl = await WatchlistService.get_watchlist(
            db, current_user=current_user, watchlist_id=watchlist_id
        )
        await WatchlistService._ensure_symbol_exists(db, symbol_id=item_in.symbol_id)

        dup_stmt = (
            select(WatchlistItem)
            .where(
                WatchlistItem.watchlist_id == wl.id,
                WatchlistItem.symbol_id == item_in.symbol_id,
            )
            .limit(1)
        )
        dup_res = await db.execute(dup_stmt)
        if dup_res.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409,
                detail="Symbol already exists in this watchlist",
            )

        item = WatchlistItem(watchlist_id=wl.id, symbol_id=item_in.symbol_id)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def remove_item(
        db: AsyncSession,
        *,
        current_user: User,
        item_id: UUID,
    ) -> None:
        """Remove an item by id, enforcing ownership via its watchlist."""
        stmt = (
            select(WatchlistItem)
            .join(Watchlist, Watchlist.id == WatchlistItem.watchlist_id)
            .where(
                WatchlistItem.id == item_id,
                Watchlist.user_id == current_user.id,
                Watchlist.deleted_at.is_(None),
            )
            .limit(1)
        )
        res = await db.execute(stmt)
        item = res.scalar_one_or_none()
        if item is None:
            # Determine if it exists but belongs to another user.
            stmt_any = (
                select(WatchlistItem)
                .join(Watchlist, Watchlist.id == WatchlistItem.watchlist_id)
                .where(WatchlistItem.id == item_id, Watchlist.deleted_at.is_(None))
                .limit(1)
            )
            res_any = await db.execute(stmt_any)
            if res_any.scalar_one_or_none() is None:
                raise HTTPException(status_code=404, detail="Watchlist item not found")
            raise HTTPException(status_code=403, detail="Forbidden")

        await db.delete(item)
        await db.commit()

    @staticmethod
    async def _get_item_count(db: AsyncSession, *, watchlist_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(WatchlistItem)
            .where(WatchlistItem.watchlist_id == watchlist_id)
        )
        res = await db.execute(stmt)
        return int(res.scalar_one())

