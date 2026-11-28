"""Persist online practice attempts and accepted mutations."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0015_exam_attempts"
down_revision = "0014_exam_chat_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    payload = sa.JSON().with_variant(JSONB(), "postgresql")
    op.create_table(
        "exam_attempts",
        sa.Column("attempt_id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("graded_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("reason", sa.String(10)),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("snapshot", payload, nullable=False),
        sa.Column("key", payload, nullable=False),
        sa.Column("progress", payload, nullable=False),
        sa.Column("result", payload),
    )
    op.create_index("ix_exam_attempts_user_id", "exam_attempts", ["user_id"])
    op.create_index("ix_exam_attempts_draft_id", "exam_attempts", ["draft_id"])
    op.create_index("ix_exam_attempt_due", "exam_attempts", ["status", "deadline_at"])
    active = sa.text("status = 'in_progress'")
    op.create_index("uq_exam_attempt_active", "exam_attempts", ["user_id", "draft_id"],
                    unique=True, postgresql_where=active, sqlite_where=active)
    op.create_table(
        "exam_attempt_mutations",
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("exam_attempts.attempt_id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("mutation_id", sa.String(36), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("exam_attempt_mutations")
    op.drop_table("exam_attempts")
