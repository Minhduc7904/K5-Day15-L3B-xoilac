"""Duyệt 12 mẫu giữa kỳ / cuối kỳ do migration 0019 nạp (khối 10, 11, 12, năm học 2025-2026).

Pipeline học sinh chỉ tra mẫu APPROVED nên mẫu DRAFT khiến chat trả "Chưa có mẫu đã duyệt phù hợp".
Chỉ đổi dòng còn DRAFT, nên không ghi đè mẫu admin đã sửa hoặc đã duyệt. Cột `source` vẫn ghi rõ phần nào
là (tự ước tính). Downgrade đưa đúng các dòng đó về DRAFT.

Revision ID: 0021_approve_seed_templates
Revises: 0020_users_is_root
"""
from alembic import op

revision = "0021_approve_seed_templates"
down_revision = "0020_users_is_root"
branch_labels = None
depends_on = None

SEED_SEMESTER = (
    "name LIKE 'Toán % (2025-2026)' AND version_label = '2025-2026' "
    "AND exam_type IN ('GK1','CK1','GK2','CK2') AND grade IN (10, 11, 12)"
)


def upgrade() -> None:
    op.execute(
        f"UPDATE exam_templates SET status = 'APPROVED', approved_at = now(), updated_at = now() "
        f"WHERE status = 'DRAFT' AND {SEED_SEMESTER}"
    )


def downgrade() -> None:
    op.execute(
        f"UPDATE exam_templates SET status = 'DRAFT', approved_at = NULL, updated_at = now() "
        f"WHERE status = 'APPROVED' AND {SEED_SEMESTER}"
    )
