from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.database.session import get_db
from app.models import User
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemListResponse,
    WatchlistItemResponse,
    WatchlistResponse,
    WatchlistUpdate,
)
from app.services.watchlist_service import WatchlistService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


def _parse_uuid(value: str, *, field: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {field}",
        ) from exc


@router.get("", response_model=List[WatchlistResponse])
async def list_watchlists(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[WatchlistResponse]:
    watchlists = await WatchlistService.list_watchlists(db, current_user=current_user)
    return [
        WatchlistResponse(
            id=wl.id,
            user_id=wl.user_id,
            name=wl.name,
            item_count=await WatchlistService._get_item_count(db, watchlist_id=wl.id),
            created_at=wl.created_at,
            updated_at=wl.updated_at,
        )
        for wl in watchlists
    ]


@router.get("/{id}", response_model=WatchlistResponse)
async def get_watchlist(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WatchlistResponse:
    wid = _parse_uuid(id, field="watchlist id")
    wl = await WatchlistService.get_watchlist(db, current_user=current_user, watchlist_id=wid)
    return WatchlistResponse(
        id=wl.id,
        user_id=wl.user_id,
        name=wl.name,
        item_count=await WatchlistService._get_item_count(db, watchlist_id=wid),
        created_at=wl.created_at,
        updated_at=wl.updated_at,
    )


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    watchlist_in: WatchlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WatchlistResponse:
    wl = await WatchlistService.create_watchlist(
        db,
        current_user=current_user,
        watchlist_in=watchlist_in,
    )
    return WatchlistResponse(
        id=wl.id,
        user_id=wl.user_id,
        name=wl.name,
        item_count=await WatchlistService._get_item_count(db, watchlist_id=wl.id),
        created_at=wl.created_at,
        updated_at=wl.updated_at,
    )


@router.patch("/{id}", response_model=WatchlistResponse)
async def update_watchlist(
    id: str,
    watchlist_in: WatchlistUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WatchlistResponse:
    wid = _parse_uuid(id, field="watchlist id")
    wl = await WatchlistService.update_watchlist(
        db,
        current_user=current_user,
        watchlist_id=wid,
        watchlist_in=watchlist_in,
    )
    return WatchlistResponse(
        id=wl.id,
        user_id=wl.user_id,
        name=wl.name,
        item_count=await WatchlistService._get_item_count(db, watchlist_id=wid),
        created_at=wl.created_at,
        updated_at=wl.updated_at,
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    wid = _parse_uuid(id, field="watchlist id")
    await WatchlistService.delete_watchlist(db, current_user=current_user, watchlist_id=wid)


@router.get("/{watchlist_id}/items", response_model=WatchlistItemListResponse)
async def list_items(
    watchlist_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WatchlistItemListResponse:
    wid = _parse_uuid(watchlist_id, field="watchlist id")
    items = await WatchlistService.list_items(db, current_user=current_user, watchlist_id=wid)
    return WatchlistItemListResponse(
        items=[WatchlistItemResponse.model_validate(i) for i in items]
    )


@router.post(
    "/{watchlist_id}/items",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_item(
    watchlist_id: str,
    item_in: WatchlistItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WatchlistItemResponse:
    wid = _parse_uuid(watchlist_id, field="watchlist id")
    item = await WatchlistService.add_item(
        db,
        current_user=current_user,
        watchlist_id=wid,
        item_in=item_in,
    )
    return WatchlistItemResponse.model_validate(item)


@router.delete("/watchlist-items/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    iid = _parse_uuid(id, field="watchlist item id")
    await WatchlistService.remove_item(db, current_user=current_user, item_id=iid)

