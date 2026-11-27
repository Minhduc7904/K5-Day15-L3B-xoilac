"""bảng phiên chat tạo đề, tin nhắn, bản xem trước, đề nháp (issue #4)

Nối sau 0005_exam_templates (#5), vốn nối sau 0005_student_auth (#25) và 0004 (auth #8). PR #4 phải merge sau PR #5.
Nếu trước lúc merge main có thêm migration khác, đổi down_revision trỏ vào migration mới nhất trên main, nếu không
Alembic có hai head và `alembic upgrade head` báo lỗi khi deploy.

Revision ID: 0006_exam_chat
Revises: 0005_exam_templates
Create Date: 2026-11-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_exam_chat"
down_revision = "0005_exam_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exam_chat_sessions",
        sa.Column("session_id", sa.Integer(), primary_key=True),
        # Chủ phiên: tài khoản học sinh (Auth #8). Xoá tài khoản thì xoá luôn phiên và dữ liệu chat của tài khoản đó.
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.user_id", ondelete="CASCADE", name="fk_exam_chat_sessions_user_id"),
                  nullable=True),
        sa.Column("student_ref", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_exam_chat_sessions_user_id", "exam_chat_sessions", ["user_id"])
    op.create_index("ix_exam_chat_sessions_student_ref", "exam_chat_sessions", ["student_ref"])

    op.create_table(
        "exam_chat_messages",
        sa.Column("message_id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(),
                  sa.ForeignKey("exam_chat_sessions.session_id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("preview_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('student','assistant')", name="ck_exam_chat_messages_role"),
    )
    op.create_index("ix_exam_chat_messages_session_id", "exam_chat_messages", ["session_id"])

    op.create_table(
        "exam_previews",
        sa.Column("session_id", sa.Integer(),
                  sa.ForeignKey("exam_chat_sessions.session_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("mode", sa.String(20), nullable=False, server_default="CHAPTER"),
        sa.Column("structure", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="PROPOSED"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('PROPOSED','EDITED','CONFIRMED','BUILT')", name="ck_exam_previews_status"),
        sa.CheckConstraint("mode IN ('CHAPTER','EXAM_TEMPLATE')", name="ck_exam_previews_mode"),
    )

    op.create_table(
        "exam_drafts",
        sa.Column("draft_id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(),
                  sa.ForeignKey("exam_chat_sessions.session_id", ondelete="CASCADE"), nullable=False),
        sa.Column("preview_version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("structure", postgresql.JSONB(), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("shortages", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_exam_drafts_session_id", "exam_drafts", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_exam_drafts_session_id", table_name="exam_drafts")
    op.drop_table("exam_drafts")
    op.drop_table("exam_previews")
    op.drop_index("ix_exam_chat_messages_session_id", table_name="exam_chat_messages")
    op.drop_table("exam_chat_messages")
    op.drop_index("ix_exam_chat_sessions_student_ref", table_name="exam_chat_sessions")
    op.drop_index("ix_exam_chat_sessions_user_id", table_name="exam_chat_sessions")
    op.drop_table("exam_chat_sessions")
