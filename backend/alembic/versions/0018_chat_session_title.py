"""Let students rename and hide exam chat sessions.

`title` is the name the student chose (the list falls back to the first message). `deleted_at` hides a session
without deleting its drafts, so exams already built stay in "Đề của tôi" and their attempts keep working.
"""
import sqlalchemy as sa
from alembic import op

revision = "0018_chat_session_title"
down_revision = "0017_preview_cancelled"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("exam_chat_sessions", sa.Column("title", sa.String(80), nullable=True))
    op.add_column("exam_chat_sessions", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("exam_chat_sessions", "deleted_at")
    op.drop_column("exam_chat_sessions", "title")
