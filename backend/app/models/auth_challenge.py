from datetime import datetime

from sqlalchemy import JSON, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmailChallenge(Base):
    __tablename__ = "email_challenges"
    __table_args__ = (UniqueConstraint("challenge_hash", name="uq_email_challenges_hash"),)

    purpose: Mapped[str] = mapped_column(String(20), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    challenge_hash: Mapped[str | None] = mapped_column(String(64))
    otp_hash: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict | None] = mapped_column(JSON)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sends: Mapped[int] = mapped_column(default=0, server_default="0")
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")


class GoogleHandoff(Base):
    __tablename__ = "google_handoffs"

    ticket_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    browser_challenge: Mapped[str] = mapped_column(String(43))
    payload: Mapped[dict] = mapped_column(JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
