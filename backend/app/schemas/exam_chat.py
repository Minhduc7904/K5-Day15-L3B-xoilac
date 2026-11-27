"""Schema request/response cho pipeline học sinh tạo đề ôn (issue #4)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.usecase.exam_preview_rules import PreviewEdit, PreviewStructure


class SessionCreate(BaseModel):
    # Tạm thời client gửi mã học sinh. Khi có Auth (#8), lấy từ tài khoản đăng nhập và bỏ trường này.
    student_ref: str = Field(min_length=1, max_length=64)


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
    structure: PreviewStructure
    status: Literal["PROPOSED", "EDITED", "CONFIRMED", "BUILT"]
    version: int
    reason: str | None
    updated_at: datetime


class PreviewUpdate(BaseModel):
    """Chỉnh bản xem trước từ giao diện. version là bản client đang thấy; lệch thì 409."""

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
    chapter: str
    difficulty: str | None
    type: str
    content: str
    statements: list[DraftStatement]


class Shortage(BaseModel):
    chapter: str
    difficulty: str
    requested: int
    available: int


class DraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    draft_id: int
    session_id: int
    preview_version: int
    title: str
    structure: PreviewStructure
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
