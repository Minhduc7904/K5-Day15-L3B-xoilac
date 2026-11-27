"""Track MinIO images attached to student chat messages."""
import sqlalchemy as sa
from alembic import op

revision = "0014_exam_chat_images"
down_revision = "0013_live_exam_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exam_chat_attachments",
        sa.Column("attachment_id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(),
                  sa.ForeignKey("exam_chat_messages.message_id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(20), nullable=False),
        sa.Column("object_key", sa.String(255), nullable=False),
        sa.UniqueConstraint("message_id", "position", name="uq_exam_chat_attachment_position"),
    )


def downgrade() -> None:
    op.drop_table("exam_chat_attachments")
