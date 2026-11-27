from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sample_item import SampleItem


class SampleItemRepository:
    """Chỉ truy cập DB. Không chứa luật nghiệp vụ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, name: str) -> SampleItem:
        item = SampleItem(name=name)
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def get(self, item_id: int) -> SampleItem | None:
        return await self._session.get(SampleItem, item_id)

    async def list(self, limit: int = 50) -> Sequence[SampleItem]:
        result = await self._session.execute(select(SampleItem).order_by(SampleItem.id.desc()).limit(limit))
        return result.scalars().all()
