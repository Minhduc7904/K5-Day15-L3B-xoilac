"""Schema request/response cho mẫu cấu trúc đề (issue #5).

Schema chỉ kiểm hình dạng và miền giá trị của từng trường. Luật liên trường (tổng số câu, khối lớp theo loại
kỳ thi, chương theo khối, nguồn khi duyệt) nằm ở app/usecase/exam_template_rules.py.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExamType = Literal["GK1", "GK2", "CK1", "CK2", "THPT", "HSA", "TSA"]
QuestionType = Literal["SINGLE_CHOICE", "MULTIPLE_CHOICE", "TRUE_FALSE", "SHORT_ANSWER", "ESSAY"]
Difficulty = Literal["NB", "TH", "VD", "VDC"]
TemplateStatus = Literal["DRAFT", "APPROVED"]


class TemplateSection(BaseModel):
    """Một phần của đề: cùng một loại câu, số câu cố định."""

    order: int = Field(ge=1, le=50)
    title: str = Field(min_length=1, max_length=255)
    question_type: QuestionType
    count: int = Field(ge=1, le=100)
    points_per_question: float | None = Field(default=None, gt=0, le=10)
    difficulty_distribution: dict[Difficulty, int] | None = None
    chapter_codes: list[str] | None = None


class ExamTemplateIn(BaseModel):
    """Dùng cho cả tạo và sửa (sửa là thay toàn bộ nội dung mẫu)."""

    name: str = Field(min_length=1, max_length=255)
    exam_type: ExamType
    grade: int | None = Field(default=None, ge=10, le=12)
    version_label: str | None = Field(default=None, max_length=50)
    duration_minutes: int | None = Field(default=None, ge=1, le=300)
    source: str | None = Field(default=None, max_length=2000)
    description: str | None = Field(default=None, max_length=5000)
    sections: list[TemplateSection] = Field(min_length=1, max_length=20)


class ExamTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_id: int
    name: str
    exam_type: ExamType
    grade: int | None
    version_label: str | None
    duration_minutes: int | None
    source: str | None
    description: str | None
    sections: list[TemplateSection]
    total_questions: int
    status: TemplateStatus
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
