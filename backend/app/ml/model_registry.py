from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class LoadedModel:
    """A loaded model ready for inference.

    In this scaffold we keep the payload generic. Concrete model loading can
    be wired later.
    """

    model: object


class ModelRegistry:
    """Adapter around the ORM-backed MLModel table.

    This file exists to stabilize imports and keep model loading logic
    isolated from API routes and ORM models.
    """

    def __init__(self, *, model_loader: Optional[callable] = None):
        self._model_loader = model_loader

    async def load(self, *, model_id: UUID) -> LoadedModel:
        if self._model_loader is None:
            # Scaffold: return a dummy object. Real loading can be added later.
            return LoadedModel(model={"model_id": str(model_id)})

        loaded = await self._model_loader(model_id)
        return LoadedModel(model=loaded)

