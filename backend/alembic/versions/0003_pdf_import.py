"""Phiên nhập PDF và bản nháp của Issue #3.

Revision ID: 0003_pdf_import
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_pdf_import"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pdf_imports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("original_media_id", sa.Integer, sa.ForeignKey("media.media_id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("page_count", sa.Integer, nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("stage", sa.String(24), nullable=False),
        sa.Column("error", sa.String, nullable=True),
        sa.Column("pages", sa.JSON, nullable=False),
        sa.Column("warnings", sa.JSON, nullable=False),
        sa.Column("ocr_model", sa.String, nullable=True),
        sa.Column("extraction_model", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "pdf_import_drafts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("import_id", sa.Integer, sa.ForeignKey("pdf_imports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.question_id"), unique=True),
    )
    op.create_index("ix_pdf_import_drafts_import_id", "pdf_import_drafts", ["import_id"])


def downgrade() -> None:
    op.drop_table("pdf_import_drafts")
    op.drop_table("pdf_imports")
