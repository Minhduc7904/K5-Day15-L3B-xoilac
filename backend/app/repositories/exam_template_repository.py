from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam_template import ExamTemplate


class ExamTemplateRepository:
    """Chỉ truy cập DB. Không chứa luật nghiệp vụ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, values: dict[str, Any]) -> ExamTemplate:
        item = ExamTemplate(**values)
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def get(self, template_id: int) -> ExamTemplate | None:
        return await self._session.get(ExamTemplate, template_id)

    async def update(self, item: ExamTemplate, values: dict[str, Any]) -> ExamTemplate:
        for key, value in values.items():
            setattr(item, key, value)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def set_status(self, item: ExamTemplate, status: str, approved_at: datetime | None) -> ExamTemplate:
        return await self.update(item, {"status": status, "approved_at": approved_at})

    async def list(
        self,
        *,
        status: str | None = None,
        exam_type: str | None = None,
        grade: int | None = None,
        version_label: str | None = None,
        limit: int = 100,
    ) -> Sequence[ExamTemplate]:
        stmt = select(ExamTemplate)
        if status is not None:
            stmt = stmt.where(ExamTemplate.status == status)
        if exam_type is not None:
            stmt = stmt.where(ExamTemplate.exam_type == exam_type)
        if grade is not None:
            stmt = stmt.where(ExamTemplate.grade == grade)
        if version_label is not None:
            stmt = stmt.where(ExamTemplate.version_label == version_label)
        stmt = stmt.order_by(ExamTemplate.updated_at.desc(), ExamTemplate.template_id.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()
