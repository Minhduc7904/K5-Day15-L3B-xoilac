"""Schema request/response cho pipeline học sinh tạo đề ôn (issue #4)."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.usecase.exam_preview_rules import PreviewEdit, PreviewStructure
from app.usecase.exam_template_plan import TemplatePreviewStructure

# Bản xem trước ở một trong hai dạng, phân biệt bằng trường "kind" (CHAPTER | EXAM_TEMPLATE).
AnyStructure = Annotated[PreviewStructure | TemplatePreviewStructure, Field(discriminator="kind")]


class SessionCreate(BaseModel):
    """Qua API luôn có đăng nhập (Auth #8): student_ref lấy từ tài khoản, trường này bị bỏ qua và có thể bỏ trống.

    Chỉ dùng khi chạy use case không qua đăng nhập (test logic)."""

    student_ref: str | None = Field(default=None, min_length=1, max_length=64)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: int
    student_ref: str
    created_at: datetime


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: int
    role: Literal["student", "assistant"]
    content: str
    preview_version: int | None
    created_at: datetime


class PreviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: int
    mode: Literal["CHAPTER", "EXAM_TEMPLATE"]
    structure: AnyStructure
    status: Literal["PROPOSED", "EDITED", "CONFIRMED", "BUILT"]
    version: int
    reason: str | None
    updated_at: datetime


class PreviewUpdate(BaseModel):
    """Chỉnh bản xem trước từ giao diện. version là bản client đang thấy; lệch thì 409.

    Với bản theo mẫu kỳ thi chỉ được thu hẹp chương (edit.chapter_codes); trường khác trả 422 kèm lý do."""

    version: int = Field(ge=1)
    edit: PreviewEdit


class ConfirmIn(BaseModel):
    version: int = Field(ge=1)


class DraftStatement(BaseModel):
    order: int | None
    content: str


class DraftItem(BaseModel):
    """Một câu trong đề nháp. Cố ý không có đáp án, cờ đúng/sai hay lời giải."""

    order: int
    question_id: int
    code: str
    chapter: str | None
    chapter_codes: list[str] = Field(default_factory=list)
    difficulty: str | None
    type: str
    content: str
    statements: list[DraftStatement]
    section_order: int | None = None      # chỉ có ở đề theo mẫu kỳ thi
    section_title: str | None = None
    points: float | None = None


class Shortage(BaseModel):
    """Phần ngân hàng không đủ câu. Đề theo chương: chapter + difficulty. Đề theo mẫu: thêm section_*, question_type."""

    chapter: str | None = None
    difficulty: str | None = None
    requested: int
    available: int
    section_order: int | None = None
    section_title: str | None = None
    question_type: str | None = None


class DraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    draft_id: int
    session_id: int
    preview_version: int
    title: str
    structure: AnyStructure
    items: list[DraftItem]
    shortages: list[Shortage]
    created_at: datetime


class ConfirmOut(BaseModel):
    preview: PreviewOut
    draft: DraftOut | None
    message: str


class SessionStateOut(BaseModel):
    session: SessionOut
    messages: list[MessageOut]
    preview: PreviewOut | None
    draft: DraftOut | None
