"""Keep one current draft per session and record first-build charges."""
import sqlalchemy as sa
from alembic import op

revision = "0013_live_exam_chat"
down_revision = "0012_backfill_parent_chapters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("exam_drafts", sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.execute("""
        UPDATE exam_drafts SET is_current = false
        WHERE draft_id NOT IN (SELECT max(draft_id) FROM exam_drafts GROUP BY session_id)
    """)
    op.create_index("uq_exam_draft_current", "exam_drafts", ["session_id"], unique=True,
                    postgresql_where=sa.text("is_current"), sqlite_where=sa.text("is_current"))
    op.add_column("credit_ledger", sa.Column("exam_session_id", sa.Integer(), nullable=True))
    op.create_index("uq_credit_exam_session", "credit_ledger", ["exam_session_id"], unique=True)
    op.add_column("exam_previews", sa.Column("operation", sa.JSON(), nullable=True))
    op.add_column("exam_previews", sa.Column("offer", sa.JSON(), nullable=True))
    op.add_column("exam_previews", sa.Column("original_structure", sa.JSON(), nullable=True))
    op.add_column("exam_chat_sessions", sa.Column("context_summary", sa.Text(), nullable=True))
    op.add_column("exam_chat_sessions", sa.Column("summarized_through", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("exam_chat_sessions", "summarized_through")
    op.drop_column("exam_chat_sessions", "context_summary")
    op.drop_column("exam_previews", "original_structure")
    op.drop_column("exam_previews", "offer")
    op.drop_column("exam_previews", "operation")
    op.drop_index("uq_credit_exam_session", table_name="credit_ledger")
    op.drop_column("credit_ledger", "exam_session_id")
    op.drop_index("uq_exam_draft_current", table_name="exam_drafts")
    op.drop_column("exam_drafts", "is_current")
