from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from fastapi import HTTPException

from app.services.historical_price_service import HistoricalPriceService


@pytest.mark.asyncio
async def test_validate_period_invalid() -> None:
    with pytest.raises(HTTPException) as exc:
        HistoricalPriceService._validate_period("yearly")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_date_range_invalid() -> None:
    with pytest.raises(HTTPException) as exc:
        HistoricalPriceService._validate_date_range(
            period="daily", start_date=date(2024, 1, 2), end_date=date(2024, 1, 1)
        )
    assert exc.value.status_code == 400

