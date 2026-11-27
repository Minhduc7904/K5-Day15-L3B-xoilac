"""Bảng của pipeline học sinh tạo đề ôn (issue #4): phiên chat, tin nhắn, bản xem trước, đề nháp."""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")


class ExamChatSession(Base):
    """Một phiên hội thoại tạo đề.

    user_id: chủ phiên (tài khoản học sinh đăng nhập, Auth #8). Chưa có Auth thì NULL và student_ref do client gửi.
    Không đặt khoá ngoại tới bảng users vì bảng đó thuộc migration của #8, chưa có trên main; thêm khi #8 merge.
    """

    __tablename__ = "exam_chat_sessions"

    session_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    student_ref: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExamChatMessage(Base):
    __tablename__ = "exam_chat_messages"

    message_id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("exam_chat_sessions.session_id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(10))  # student | assistant
    content: Mapped[str] = mapped_column(Text)
    preview_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExamPreview(Base):
    """Bản xem trước hiện tại của phiên (một phiên một bản). version tăng mỗi lần đổi để chặn ghi đè giữa chat và API."""

    __tablename__ = "exam_previews"

    session_id: Mapped[int] = mapped_column(
        ForeignKey("exam_chat_sessions.session_id", ondelete="CASCADE"), primary_key=True
    )
    mode: Mapped[str] = mapped_column(String(20), default="CHAPTER")  # CHAPTER | EXAM_TEMPLATE
    structure: Mapped[dict[str, Any]] = mapped_column(JsonType)
    status: Mapped[str] = mapped_column(String(10), default="PROPOSED")
    version: Mapped[int] = mapped_column(Integer, default=1)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExamDraft(Base):
    """Đề nháp đã dựng từ một bản xem trước đã xác nhận. items không chứa đáp án hay lời giải."""

    __tablename__ = "exam_drafts"

    draft_id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("exam_chat_sessions.session_id", ondelete="CASCADE"), index=True
    )
    preview_version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    structure: Mapped[dict[str, Any]] = mapped_column(JsonType)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JsonType)
    shortages: Mapped[list[dict[str, Any]]] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
