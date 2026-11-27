"""Gắn chương cha cho các câu hỏi đã có chương con nhưng chưa có chương cha.

Cây chương (xem data/chapters.csv): chương cha là `level = 0` (vd 10C1 "MỆNH ĐỀ VÀ TẬP HỢP"),
chương con là `level = 1` và trỏ về cha qua `parent_chapter_id` (vd 10C11 "Mệnh đề" -> 10C1).
Nhiều câu hỏi chỉ được gắn chương con, nên lọc theo chương cha (đề theo chương lớn) bị sót.

Migration chèn thêm dòng `questions_chapters (question_id, parent_chapter_id)` cho mọi tổ tiên
của chương con đang gắn mà câu hỏi chưa có. Dùng đệ quy nên vẫn đúng nếu sau này cây sâu hơn
2 cấp. Không xoá, không sửa dòng nào có sẵn; chạy lại nhiều lần không sinh dòng trùng
(ON CONFLICT DO NOTHING). Gói seed nền được nạp SAU migration (db-init), nên trên DB mới
chưa có dữ liệu thì migration này không làm gì; lúc đó chạy lại câu lệnh INSERT bên dưới
sau khi nạp seed.

Revision ID: 0012_backfill_parent_chapters
Revises: 0011_student_profiles
"""
from alembic import op

revision = "0012_backfill_parent_chapters"
down_revision = "0011_student_profiles"
branch_labels = None
depends_on = None

BACKFILL_PARENT_CHAPTERS = """
WITH RECURSIVE ancestors (question_id, chapter_id) AS (
    SELECT qc.question_id, c.parent_chapter_id
    FROM questions_chapters qc
    JOIN chapters c ON c.chapter_id = qc.chapter_id
    WHERE c.parent_chapter_id IS NOT NULL
    UNION
    SELECT a.question_id, c.parent_chapter_id
    FROM ancestors a
    JOIN chapters c ON c.chapter_id = a.chapter_id
    WHERE c.parent_chapter_id IS NOT NULL
)
INSERT INTO questions_chapters (question_id, chapter_id)
SELECT question_id, chapter_id FROM ancestors
ON CONFLICT (question_id, chapter_id) DO NOTHING
"""


def upgrade() -> None:
    op.execute(BACKFILL_PARENT_CHAPTERS)


def downgrade() -> None:
    # Không thể phân biệt dòng chương cha do migration thêm với dòng đã có từ trước,
    # và xoá nhầm sẽ làm mất liên kết gốc, nên không hoàn tác dữ liệu.
    pass
