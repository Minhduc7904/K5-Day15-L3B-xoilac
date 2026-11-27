"""Nguồn bên ngoài mà pipeline học sinh (#4) cần nhưng chưa có chủ sở hữu hoặc chưa sẵn sàng.

Mỗi nguồn là một giao diện nhỏ, kèm cài đặt mặc định an toàn để backend chạy được ngay:

- Lịch sử làm bài: chưa có bảng kết quả làm bài trong DB (dữ liệu nền không có học sinh). Mặc định NoHistory,
  agent sẽ nói chưa có lịch sử và hỏi chương, không đoán (giống ca B05). StaticHistory dùng cho test và demo.
- Mẫu cấu trúc đề: thuộc issue #5, nối qua TemplateLookupSource(ExamTemplateUseCase.lookup) trong deps.py.
  NoTemplates (không có mẫu nào, agent nói chưa có cấu trúc đã xác thực như ca B09) chỉ dùng cho test.
- Diễn đạt lại bằng model: chưa chốt nhà cung cấp và key. Mặc định PlainReplyWriter trả nguyên văn bản dựng bằng code.
"""
from collections.abc import Awaitable, Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

CONFLICT_RATIO = 0.25  # giống codebase/tools.py: ≥ 25% câu trái kết quả trong cùng lượt → mâu thuẫn


@dataclass
class ChapterResult:
    code: str
    correct: int
    total: int

    @property
    def rate(self) -> float:
        return self.correct / self.total if self.total else 0.0


@dataclass
class StudentHistory:
    chapters: list[ChapterResult] = field(default_factory=list)
    conflict_ratio: float = 0.0

    @property
    def conflicting(self) -> bool:
        return self.conflict_ratio >= CONFLICT_RATIO


class StudentHistorySource(Protocol):
    async def get(self, student_ref: str) -> StudentHistory | None: ...


class NoHistory:
    async def get(self, student_ref: str) -> StudentHistory | None:
        return None


class StaticHistory:
    """Lịch sử dựng sẵn trong bộ nhớ (test, demo). Không phải dữ liệu học sinh thật."""

    def __init__(self, data: dict[str, StudentHistory]) -> None:
        self._data = data

    async def get(self, student_ref: str) -> StudentHistory | None:
        return self._data.get(student_ref)


class ExamTemplateSource(Protocol):
    async def find(self, exam_type: str, grade: int | None, version_label: str | None) -> list[dict]: ...


class NoTemplates:
    async def find(self, exam_type: str, grade: int | None, version_label: str | None) -> list[dict]:
        return []


TEMPLATE_FIELDS = ("template_id", "name", "exam_type", "grade", "version_label", "duration_minutes", "source",
                   "sections", "total_questions", "status")


def template_to_dict(item: Any) -> dict:
    """Đổi một mẫu (dict, hoặc model ORM ExamTemplate của #5) về dict theo hợp đồng ExamTemplateOut."""
    if isinstance(item, dict):
        return {k: item.get(k) for k in TEMPLATE_FIELDS}
    return {k: getattr(item, k, None) for k in TEMPLATE_FIELDS}


class TemplateLookupSource:
    """Nối với tra cứu mẫu đã duyệt của #5. lookup là ExamTemplateUseCase.lookup (hoặc hàm cùng chữ ký):
    async lookup(*, exam_type, grade, version_label) -> danh sách mẫu APPROVED.

    Chỉ giữ mẫu có status APPROVED, phòng khi nguồn trả nhầm mẫu nháp."""

    def __init__(self, lookup: Callable[..., Awaitable[Sequence[Any]]]) -> None:
        self._lookup = lookup

    async def find(self, exam_type: str, grade: int | None, version_label: str | None) -> list[dict]:
        items = await self._lookup(exam_type=exam_type, grade=grade, version_label=version_label)
        return [d for d in (template_to_dict(t) for t in items) if d.get("status") in (None, "APPROVED")]


class ReplyWriter(Protocol):
    def stream(self, text: str) -> Iterator[str]: ...


class PlainReplyWriter:
    """Không gọi model: chia văn bản dựng bằng code thành từng dòng để phát qua SSE."""

    def stream(self, text: str) -> Iterator[str]:
        lines = text.split("\n")
        for i, line in enumerate(lines):
            yield line + ("\n" if i < len(lines) - 1 else "")
