from datetime import date, datetime, time

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Time, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint("grade IN (10, 11, 12)", name="ck_student_profile_grade"),
        CheckConstraint("target_score IN (7, 8, 9)", name="ck_student_profile_target"),
        CheckConstraint(
            "exam_period IN ('midterm_1','final_1','midterm_2','final_2','national_high_school')",
            name="ck_student_profile_exam",
        ),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    school_name: Mapped[str] = mapped_column(String(200))
    grade: Mapped[int]
    target_score: Mapped[int]
    exam_period: Mapped[str] = mapped_column(String(24))
    reminder_time: Mapped[time | None] = mapped_column(Time)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StudentStudyDay(Base):
    __tablename__ = "student_study_days"
    __table_args__ = (CheckConstraint("weekday BETWEEN 1 AND 6", name="ck_student_study_weekday"),)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.user_id", ondelete="CASCADE"), primary_key=True
    )
    weekday: Mapped[int] = mapped_column(primary_key=True)


class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    __table_args__ = (
        CheckConstraint("balance BETWEEN 0 AND 500", name="ck_credit_account_balance"),
        Index("ix_credit_account_daily", "last_daily_processed_on", "user_id"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    balance: Mapped[int]
    last_daily_processed_on: Mapped[date] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CreditLedger(Base):
    __tablename__ = "credit_ledger"
    __table_args__ = (
        CheckConstraint("delta <> 0", name="ck_credit_ledger_delta"),
        CheckConstraint("balance_after BETWEEN 0 AND 500", name="ck_credit_ledger_balance"),
        Index("ix_credit_ledger_history", "user_id", "id"),
        Index(
            "uq_credit_initial", "user_id", unique=True,
            postgresql_where=text("reason = 'initial_grant'"), sqlite_where=text("reason = 'initial_grant'"),
        ),
        Index(
            "uq_credit_daily", "user_id", "effective_on", unique=True,
            postgresql_where=text("reason = 'daily_grant'"), sqlite_where=text("reason = 'daily_grant'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("credit_accounts.user_id", ondelete="CASCADE"))
    delta: Mapped[int]
    balance_after: Mapped[int]
    reason: Mapped[str] = mapped_column(String(32))
    effective_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudyReminderDelivery(Base):
    __tablename__ = "study_reminder_deliveries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','sending','sent','failed','uncertain','expired')",
            name="ck_study_reminder_status",
        ),
        CheckConstraint("attempt_count BETWEEN 0 AND 3", name="ck_study_reminder_attempts"),
        Index("ix_study_reminder_due", "status", "next_attempt_at"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id", ondelete="CASCADE"), primary_key=True)
    local_date: Mapped[date] = mapped_column(Date, primary_key=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(12))
    attempt_count: Mapped[int]
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gmail_message_id: Mapped[str | None] = mapped_column(String(255))
