"""Embedding cache for approved question references.

Revision ID: 0004_pdf_import_vectors
Revises: 0003_pdf_import
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_pdf_import_vectors"
down_revision = "0003_pdf_import"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pdf_import_reference_vectors",
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.question_id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("model", sa.String(128), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("vector", sa.JSON, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("pdf_import_reference_vectors")
