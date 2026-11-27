"""Join the PDF import and student Auth migration branches.

Revision ID: 0008_pdf_import_student_auth
Revises: 0007_pdf_import_auth, 0005_student_auth
"""

revision = "0008_pdf_import_student_auth"
down_revision = ("0007_pdf_import_auth", "0005_student_auth")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
