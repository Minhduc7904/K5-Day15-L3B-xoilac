from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

ROLE_STUDENT = "student"
ROLE_ADMIN = "admin"
STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"


class User(Base):
    """Tài khoản đăng nhập. Email lưu chữ thường; duy nhất theo lower(email)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('student','admin')", name="ck_users_role"),
        CheckConstraint("status IN ('active','disabled')", name="ck_users_status"),
        Index("uq_users_email_lower", func.lower(text("email")), unique=True),
    )

    user_id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(10), default=ROLE_STUDENT, server_default=ROLE_STUDENT)
    status: Mapped[str] = mapped_column(String(10), default=STATUS_ACTIVE, server_default=STATUS_ACTIVE)
    display_name: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
