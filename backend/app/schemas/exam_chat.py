"""Schema request/response cho pipeline học sinh tạo đề ôn (issue #4)."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

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
    updated_at: datetime


class SessionListItem(SessionOut):
    title: str


class SessionRename(BaseModel):
    title: str = Field(min_length=1, max_length=80)

    @field_validator("title")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tên đoạn chat không được để trống")
        return value.strip()


class StudentPlan(BaseModel):
    """Tổng quan học sinh vừa chỉnh trên bảng cấu trúc, nhờ agent phân bổ lại thành ma trận chi tiết."""

    chapter_counts: dict[str, Annotated[int, Field(ge=1, le=50)]] = Field(default_factory=dict, max_length=20)
    type_counts: dict[str, Annotated[int, Field(ge=1, le=50)]] = Field(default_factory=dict, max_length=5)
    difficulty_counts: dict[Literal["NB", "TH", "VD", "VDC"], Annotated[int, Field(ge=0, le=50)]] = Field(default_factory=dict)


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    version: int | None = Field(None, ge=0)
    plan: StudentPlan | None = None


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attachment_id: int
    position: int
    mime_type: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: int
    role: Literal["student", "assistant"]
    content: str
    preview_version: int | None
    created_at: datetime
    attachments: list[AttachmentOut] = Field(default_factory=list)


class PreviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: int
    mode: Literal["CHAPTER", "EXAM_TEMPLATE"]
    structure: AnyStructure
    status: Literal["PROPOSED", "EDITED", "CONFIRMED", "BUILT", "CANCELLED"]
    version: int
    reason: str | None
    updated_at: datetime
    offer: dict | None = None
    operation: dict | None = None

    @field_serializer("offer")
    def public_offer(self, offer):
        return {key: value for key, value in offer.items() if key != "ids"} if offer else None


class PreviewUpdate(BaseModel):
    """Chỉnh bản xem trước từ giao diện. version là bản client đang thấy; lệch thì 409.

    Với bản theo mẫu kỳ thi chỉ được thu hẹp chương (edit.chapter_codes); trường khác trả 422 kèm lý do."""

    version: int = Field(ge=1)
    edit: PreviewEdit


class ConfirmIn(BaseModel):
    version: int = Field(ge=1)
    accepted_count: int | None = Field(None, ge=1, le=50)


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
    subchapter_codes: list[str] = Field(default_factory=list)
    difficulty: str | None
    type: str
    content: str
    statements: list[DraftStatement]
    section_order: int | None = None      # chỉ có ở đề theo mẫu kỳ thi
    section_title: str | None = None
    points: float | None = None
    max_points: float | None = None


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
    max_score: int = 10


class ConfirmOut(BaseModel):
    preview: PreviewOut
    draft: DraftOut | None
    message: str


class SessionStateOut(BaseModel):
    session: SessionOut
    messages: list[MessageOut]
    preview: PreviewOut | None
    draft: DraftOut | None
