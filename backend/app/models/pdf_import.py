from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PdfImport(Base):
    __tablename__ = "pdf_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_media_id: Mapped[int]
    filename: Mapped[str] = mapped_column(String(255))
    page_count: Mapped[int]
    status: Mapped[str] = mapped_column(String(24), default="queued")
    stage: Mapped[str] = mapped_column(String(24), default="upload")
    error: Mapped[str | None]
    pages: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    ocr_model: Mapped[str | None]
    extraction_model: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PdfDraft(Base):
    __tablename__ = "pdf_import_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("pdf_imports.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    status: Mapped[str] = mapped_column(String(16), default="pending")
    payload: Mapped[dict] = mapped_column(JSON)
    question_id: Mapped[int | None] = mapped_column(unique=True)
