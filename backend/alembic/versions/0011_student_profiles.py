"""Student profiles, credit accounts, ledger and reminder delivery."""
import sqlalchemy as sa
from alembic import op

revision = "0011_student_profiles"
down_revision = "0010_pdf_import_exam_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_profiles",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("school_name", sa.String(200), nullable=False),
        sa.Column("grade", sa.Integer, nullable=False),
        sa.Column("target_score", sa.Integer, nullable=False),
        sa.Column("exam_period", sa.String(24), nullable=False),
        sa.Column("reminder_time", sa.Time),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("grade IN (10, 11, 12)", name="ck_student_profile_grade"),
        sa.CheckConstraint("target_score IN (7, 8, 9)", name="ck_student_profile_target"),
        sa.CheckConstraint(
            "exam_period IN ('midterm_1','final_1','midterm_2','final_2','national_high_school')",
            name="ck_student_profile_exam",
        ),
    )
    op.create_table(
        "student_study_days",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("student_profiles.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("weekday", sa.Integer, primary_key=True),
        sa.CheckConstraint("weekday BETWEEN 1 AND 6", name="ck_student_study_weekday"),
    )
    op.create_table(
        "credit_accounts",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("balance", sa.Integer, nullable=False),
        sa.Column("last_daily_processed_on", sa.Date, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("balance BETWEEN 0 AND 500", name="ck_credit_account_balance"),
    )
    op.create_index("ix_credit_account_daily", "credit_accounts", ["last_daily_processed_on", "user_id"])
    op.create_table(
        "credit_ledger",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("credit_accounts.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("delta", sa.Integer, nullable=False),
        sa.Column("balance_after", sa.Integer, nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("effective_on", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("delta <> 0", name="ck_credit_ledger_delta"),
        sa.CheckConstraint("balance_after BETWEEN 0 AND 500", name="ck_credit_ledger_balance"),
    )
    op.create_index("ix_credit_ledger_history", "credit_ledger", ["user_id", "id"])
    op.create_index(
        "uq_credit_initial", "credit_ledger", ["user_id"], unique=True,
        postgresql_where=sa.text("reason = 'initial_grant'"),
    )
    op.create_index(
        "uq_credit_daily", "credit_ledger", ["user_id", "effective_on"], unique=True,
        postgresql_where=sa.text("reason = 'daily_grant'"),
    )
    op.create_table(
        "study_reminder_deliveries",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("student_profiles.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("local_date", sa.Date, primary_key=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("attempt_count", sa.Integer, nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("gmail_message_id", sa.String(255)),
        sa.CheckConstraint(
            "status IN ('pending','sending','sent','failed','uncertain','expired')",
            name="ck_study_reminder_status",
        ),
        sa.CheckConstraint("attempt_count BETWEEN 0 AND 3", name="ck_study_reminder_attempts"),
    )
    op.create_index("ix_study_reminder_due", "study_reminder_deliveries", ["status", "next_attempt_at"])
    op.execute("""
        INSERT INTO credit_accounts (user_id, balance, last_daily_processed_on)
        SELECT user_id, 500, CAST(now() AT TIME ZONE 'Asia/Ho_Chi_Minh' AS date)
        FROM users WHERE role = 'student'
    """)
    op.execute("""
        INSERT INTO credit_ledger (user_id, delta, balance_after, reason, effective_on)
        SELECT user_id, 500, balance, 'initial_grant', last_daily_processed_on FROM credit_accounts
    """)


def downgrade() -> None:
    op.drop_table("study_reminder_deliveries")
    op.drop_table("credit_ledger")
    op.drop_table("credit_accounts")
    op.drop_table("student_study_days")
    op.drop_table("student_profiles")
