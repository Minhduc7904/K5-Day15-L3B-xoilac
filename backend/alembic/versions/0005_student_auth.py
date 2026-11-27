"""Add student verification and Google sign-in.

Revision ID: 0005_student_auth
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0005_student_auth"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("google_subject", sa.String(255)))
    op.create_unique_constraint("uq_users_google_subject", "users", ["google_subject"])
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=True)
    op.create_table(
        "email_challenges",
        sa.Column("purpose", sa.String(20), primary_key=True),
        sa.Column("email", sa.String(255), primary_key=True),
        sa.Column("challenge_hash", sa.String(64)),
        sa.Column("otp_hash", sa.String(64)),
        sa.Column("payload", sa.JSON()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("window_start", sa.DateTime(timezone=True)),
        sa.Column("sends", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("challenge_hash", name="uq_email_challenges_hash"),
    )
    op.create_table(
        "google_handoffs",
        sa.Column("ticket_hash", sa.String(64), primary_key=True),
        sa.Column("browser_challenge", sa.String(43), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_google_handoffs_expires_at", "google_handoffs", ["expires_at"])


def downgrade() -> None:
    op.drop_table("google_handoffs")
    op.drop_table("email_challenges")
    # The old schema requires a hash. A sentinel cannot verify as an Argon2 password.
    op.execute("UPDATE users SET password_hash = '!' WHERE password_hash IS NULL")
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=False)
    op.drop_constraint("uq_users_google_subject", "users", type_="unique")
    op.drop_column("users", "google_subject")
    op.drop_column("users", "email_verified_at")
