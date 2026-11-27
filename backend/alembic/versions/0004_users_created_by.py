"""users.created_by: admin nào đã tạo tài khoản này (issue #8, quản lý admin)

NULL khi tài khoản tự đăng ký (student) hoặc do người vận hành tạo (ensure_admin, create_admin).
Xoá người tạo thì giữ tài khoản, chỉ đặt created_by về NULL.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-28
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN created_by integer "
        "CONSTRAINT fk_users_created_by REFERENCES users(user_id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS created_by")
