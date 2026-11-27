"""Nguồn bên ngoài mà pipeline học sinh (#4) cần nhưng chưa có chủ sở hữu hoặc chưa sẵn sàng.

Mỗi nguồn là một giao diện nhỏ, kèm cài đặt mặc định an toàn để backend chạy được ngay:

- Lịch sử làm bài: chưa có bảng kết quả làm bài trong DB (dữ liệu nền không có học sinh). Mặc định NoHistory,
  agent sẽ nói chưa có lịch sử và hỏi chương, không đoán (giống ca B05). StaticHistory dùng cho test và demo.
- Mẫu cấu trúc đề: thuộc issue #5. Mặc định NoTemplates, agent nói chưa có cấu trúc đã xác thực (giống ca B09).
  Khi #5 merge, thay bằng cài đặt gọi ExamTemplateUseCase.lookup().
- Diễn đạt lại bằng model: chưa chốt nhà cung cấp và key. Mặc định PlainReplyWriter trả nguyên văn bản dựng bằng code.
"""
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Protocol

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


class ReplyWriter(Protocol):
    def stream(self, text: str) -> Iterator[str]: ...


class PlainReplyWriter:
    """Không gọi model: chia văn bản dựng bằng code thành từng dòng để phát qua SSE."""

    def stream(self, text: str) -> Iterator[str]:
        lines = text.split("\n")
        for i, line in enumerate(lines):
            yield line + ("\n" if i < len(lines) - 1 else "")
