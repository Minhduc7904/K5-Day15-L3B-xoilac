"""bảng mẫu cấu trúc đề thi exam_templates (issue #5)

Admin tạo, sửa, duyệt mẫu. Agent pipeline học sinh (#4) chỉ tra mẫu status = 'APPROVED'.
exam_type dùng lại mã của exams.type_of_exam (migration 0002) để hai bảng nói cùng một ngôn ngữ.

Revision ID: 0005_exam_templates
Revises: 0004
Create Date: 2026-11-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_exam_templates"
down_revision = "0004"  # 0004_users_created_by (auth, #8)
branch_labels = None
depends_on = None

EXAM_TYPES = "('GK1','GK2','CK1','CK2','THPT','HSA','TSA')"


def upgrade() -> None:
    op.create_table(
        "exam_templates",
        sa.Column("template_id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("exam_type", sa.String(10), nullable=False),
        sa.Column("grade", sa.SmallInteger(), nullable=True),
        sa.Column("version_label", sa.String(50), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sections", postgresql.JSONB(), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="DRAFT"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(f"exam_type IN {EXAM_TYPES}", name="ck_exam_templates_exam_type"),
        sa.CheckConstraint("status IN ('DRAFT','APPROVED')", name="ck_exam_templates_status"),
        sa.CheckConstraint("grade IS NULL OR grade BETWEEN 10 AND 12", name="ck_exam_templates_grade"),
        sa.CheckConstraint("total_questions > 0", name="ck_exam_templates_total"),
    )
    op.create_index("idx_exam_templates_lookup", "exam_templates", ["status", "exam_type", "grade"])


def downgrade() -> None:
    op.drop_index("idx_exam_templates_lookup", table_name="exam_templates")
    op.drop_table("exam_templates")
