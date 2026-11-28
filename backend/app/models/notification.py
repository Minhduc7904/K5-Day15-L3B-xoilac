"""Thông báo trong ứng dụng cho học sinh (chuông trên header)."""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.exam_chat import JsonType


class Notification(Base):
    """Mỗi sự kiện chỉ sinh một thông báo cho mỗi người: (user_id, dedupe_key) là duy nhất."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("uq_notification_dedupe", "user_id", "dedupe_key", unique=True),
        Index("ix_notification_user_recent", "user_id", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str | None] = mapped_column(String(200))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    dedupe_key: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
