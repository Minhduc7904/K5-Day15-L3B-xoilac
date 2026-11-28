from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.exam_chat import JsonType


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"
    __table_args__ = (
        Index("uq_exam_attempt_active", "user_id", "draft_id", unique=True,
              postgresql_where=text("status = 'in_progress'"),
              sqlite_where=text("status = 'in_progress'")),
        Index("ix_exam_attempt_due", "status", "deadline_at"),
    )

    attempt_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    draft_id: Mapped[int] = mapped_column(Integer, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(12))
    reason: Mapped[str | None] = mapped_column(String(10))
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JsonType)
    key: Mapped[dict[str, Any]] = mapped_column(JsonType)
    progress: Mapped[dict[str, Any]] = mapped_column(JsonType)
    result: Mapped[dict[str, Any] | None] = mapped_column(JsonType)


class ExamAttemptMutation(Base):
    __tablename__ = "exam_attempt_mutations"

    attempt_id: Mapped[int] = mapped_column(ForeignKey("exam_attempts.attempt_id", ondelete="CASCADE"),
                                            primary_key=True)
    mutation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
