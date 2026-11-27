"""Luồng nghiệp vụ mẫu cấu trúc đề (issue #5): admin tạo, sửa, duyệt; agent (#4) tra mẫu đã duyệt.

Trạng thái: DRAFT → APPROVED. Sửa mẫu APPROVED phải vẫn đạt điều kiện duyệt, và giữ APPROVED, nên lượt tra
tiếp theo dùng ngay cấu trúc mới (nghiệm thu #5). Mẫu DRAFT không bao giờ xuất hiện trong lookup().
"""
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from app.models.exam_template import ExamTemplate
from app.repositories.exam_template_repository import ExamTemplateRepository
from app.schemas.exam_template import ExamTemplateIn
from app.usecase.exam_template_rules import ensure_valid, total_questions

APPROVED = "APPROVED"
DRAFT = "DRAFT"


def _values(data: ExamTemplateIn) -> dict[str, Any]:
    values = data.model_dump(mode="json", exclude={"sections"})
    values["sections"] = [s.model_dump(mode="json") for s in sorted(data.sections, key=lambda s: s.order)]
    values["total_questions"] = total_questions(data)
    return values


def _as_input(item: ExamTemplate) -> ExamTemplateIn:
    return ExamTemplateIn.model_validate(
        {
            "name": item.name,
            "exam_type": item.exam_type,
            "grade": item.grade,
            "version_label": item.version_label,
            "duration_minutes": item.duration_minutes,
            "source": item.source,
            "description": item.description,
            "sections": item.sections,
        }
    )


class ExamTemplateUseCase:
    def __init__(self, repo: ExamTemplateRepository) -> None:
        self._repo = repo

    async def create(self, data: ExamTemplateIn) -> ExamTemplate:
        ensure_valid(data, for_approval=False)
        return await self._repo.add({**_values(data), "status": DRAFT})

    async def get(self, template_id: int) -> ExamTemplate | None:
        return await self._repo.get(template_id)

    async def list(
        self, *, status: str | None = None, exam_type: str | None = None, grade: int | None = None
    ) -> Sequence[ExamTemplate]:
        return await self._repo.list(status=status, exam_type=exam_type, grade=grade)

    async def update(self, template_id: int, data: ExamTemplateIn) -> ExamTemplate | None:
        item = await self._repo.get(template_id)
        if item is None:
            return None
        ensure_valid(data, for_approval=item.status == APPROVED)
        return await self._repo.update(item, _values(data))

    async def approve(self, template_id: int) -> ExamTemplate | None:
        item = await self._repo.get(template_id)
        if item is None:
            return None
        if item.status == APPROVED:
            return item
        ensure_valid(_as_input(item), for_approval=True)
        return await self._repo.set_status(item, APPROVED, datetime.now(timezone.utc))

    async def lookup(
        self, *, exam_type: str, grade: int | None = None, version_label: str | None = None
    ) -> Sequence[ExamTemplate]:
        """Hợp đồng cho #4: chỉ mẫu APPROVED. Mẫu không ghi khối (grade NULL) khớp mọi khối được hỏi."""
        items = await self._repo.list(status=APPROVED, exam_type=exam_type, version_label=version_label)
        if grade is None:
            return items
        return [t for t in items if t.grade in (grade, None)]
