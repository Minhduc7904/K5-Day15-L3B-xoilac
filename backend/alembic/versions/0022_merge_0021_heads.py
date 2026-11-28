"""Gộp hai nhánh 0021 (duyệt mẫu seed, questions.archived_at) thành một head.

Hai migration 0021 cùng nối sau 0020 nên `alembic upgrade head` báo nhiều head và db-init thoát lỗi khi deploy.
Migration này không đổi schema.

Revision ID: 0022_merge_0021_heads
Revises: 0021_approve_seed_templates, 0021_questions_archived_at
"""

revision = "0022_merge_0021_heads"
down_revision = ("0021_approve_seed_templates", "0021_questions_archived_at")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
