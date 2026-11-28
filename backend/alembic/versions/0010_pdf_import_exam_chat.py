"""Join the PDF import and student exam chat migration branches.

Revision ID: 0010_pdf_import_exam_chat
Revises: 0009_pdf_import_exam_templates, 0006_exam_chat
"""

revision = "0010_pdf_import_exam_chat"
down_revision = ("0009_pdf_import_exam_templates", "0006_exam_chat")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
