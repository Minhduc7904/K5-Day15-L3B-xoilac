"""In-app notifications for students."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0016_notifications"
down_revision = "0015_exam_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("link", sa.String(200)),
        sa.Column("payload", sa.JSON().with_variant(JSONB(), "postgresql")),
        sa.Column("dedupe_key", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("uq_notification_dedupe", "notifications", ["user_id", "dedupe_key"], unique=True)
    op.create_index("ix_notification_user_recent", "notifications", ["user_id", "id"])


def downgrade() -> None:
    op.drop_table("notifications")
