"""Bảng của pipeline học sinh tạo đề ôn (issue #4): phiên chat, tin nhắn, bản xem trước, đề nháp."""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")


class ExamChatSession(Base):
    """Một phiên hội thoại tạo đề.

    user_id: chủ phiên (tài khoản học sinh đăng nhập, Auth #8). API luôn gắn chủ phiên; NULL chỉ có ở dữ liệu tạo
    không qua đăng nhập (test logic) và không ai đăng nhập đọc được phiên đó.
    student_ref: mã dùng tra lịch sử làm bài.
    """

    __tablename__ = "exam_chat_sessions"

    session_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE", name="fk_exam_chat_sessions_user_id"),
        nullable=True,
        index=True,
    )
    context_summary: Mapped[str | None] = mapped_column(Text)
    summarized_through: Mapped[int | None]
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


    attachments: Mapped[list["ExamChatAttachment"]] = relationship(
        lazy="selectin", order_by="ExamChatAttachment.position", cascade="all, delete-orphan", passive_deletes=True,
    )


class ExamChatAttachment(Base):
    __tablename__ = "exam_chat_attachments"
    __table_args__ = (UniqueConstraint("message_id", "position", name="uq_exam_chat_attachment_position"),)

    attachment_id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("exam_chat_messages.message_id", ondelete="CASCADE"))
    position: Mapped[int]
    mime_type: Mapped[str] = mapped_column(String(20))
    object_key: Mapped[str] = mapped_column(String(255))


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
    operation: Mapped[dict | None] = mapped_column(JsonType)
    offer: Mapped[dict | None] = mapped_column(JsonType)
    original_structure: Mapped[dict | None] = mapped_column(JsonType)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExamDraft(Base):
    """Đề nháp đã dựng từ một bản xem trước đã xác nhận. items không chứa đáp án hay lời giải."""

    __tablename__ = "exam_drafts"
    __table_args__ = (
        Index("uq_exam_draft_current", "session_id", unique=True,
              postgresql_where=text("is_current"), sqlite_where=text("is_current")),
    )

    is_current: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

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
