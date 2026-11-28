"""questions.archived_at: ngừng sử dụng câu hỏi mềm (issue #11)

Câu có archived_at khác NULL là "đã lưu trữ": không còn được pipeline #4 chọn cho đề mới, nhưng vẫn giữ nguyên
liên kết trong questions_exams, đề nháp và lịch sử làm bài. Không có API xoá cứng câu hỏi.
"Câu khả dụng" = visibility = 'PUBLISHED' AND archived_at IS NULL (xem question_bank_repository.available_questions).

Revision ID: 0021_questions_archived_at
Revises: 0020_users_is_root
Create Date: 2026-11-28
"""
from alembic import op

revision = "0021_questions_archived_at"
down_revision = "0020_users_is_root"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE questions ADD COLUMN archived_at timestamptz NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS archived_at")
