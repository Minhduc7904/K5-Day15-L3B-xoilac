from collections.abc import Sequence

from app.models.sample_item import SampleItem
from app.repositories.sample_item_repository import SampleItemRepository


class SampleItemUseCase:
    def __init__(self, repo: SampleItemRepository) -> None:
        self._repo = repo

    async def create(self, name: str) -> SampleItem:
        return await self._repo.add(name.strip())

    async def get(self, item_id: int) -> SampleItem | None:
        return await self._repo.get(item_id)

    async def list(self) -> Sequence[SampleItem]:
        return await self._repo.list()
