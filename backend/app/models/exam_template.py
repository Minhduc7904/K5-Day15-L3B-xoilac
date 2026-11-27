from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# JSONB trên PostgreSQL, JSON thường trên SQLite (test).
JsonType = JSON().with_variant(JSONB(), "postgresql")


class ExamTemplate(Base):
    """Mẫu cấu trúc đề thi do admin quản lý (issue #5). Agent pipeline học sinh (#4) chỉ đọc mẫu APPROVED."""

    __tablename__ = "exam_templates"
    # Khớp migration 0003 để alembic autogenerate không sinh khác biệt.
    __table_args__ = (Index("idx_exam_templates_lookup", "status", "exam_type", "grade"),)

    template_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    exam_type: Mapped[str] = mapped_column(String(10))
    grade: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    version_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JsonType)
    total_questions: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="DRAFT")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
