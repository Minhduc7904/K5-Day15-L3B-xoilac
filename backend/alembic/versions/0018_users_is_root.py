"""users.is_root: admin gốc, tối đa một tài khoản (issue #20)

Admin gốc là tài khoản tạo từ ADMIN_EMAIL/ADMIN_PASSWORD (ensure_admin). Chỉ admin gốc quản lý admin khác.
- Unique index một phần trên (is_root) WHERE is_root: không thể có hai admin gốc.
- CHECK (NOT is_root OR role = 'admin'): admin gốc không thể bị hạ vai trò, kể cả bằng SQL lỡ tay.
Không có API nào đặt is_root; chỉ ensure_admin đặt.

Revision ID: 0018_users_is_root
Revises: 0017_preview_cancelled
Create Date: 2026-11-28
"""
from alembic import op

revision = "0018_users_is_root"
down_revision = "0017_preview_cancelled"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN is_root boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE users ADD CONSTRAINT ck_users_root_is_admin CHECK (NOT is_root OR role = 'admin')")
    op.execute("CREATE UNIQUE INDEX uq_users_single_root ON users (is_root) WHERE is_root")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_single_root")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_root_is_admin")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_root")
