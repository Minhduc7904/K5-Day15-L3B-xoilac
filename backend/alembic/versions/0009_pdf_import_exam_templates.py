"""Join the PDF import and exam template migration branches.

Revision ID: 0009_pdf_import_exam_templates
Revises: 0008_pdf_import_student_auth, 0005_exam_templates
"""

revision = "0009_pdf_import_exam_templates"
down_revision = ("0008_pdf_import_student_auth", "0005_exam_templates")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
