"""Đọc ngân hàng câu hỏi nền (bảng tạo ở migration 0002) cho pipeline học sinh (#4). Chỉ đọc.

Các bảng nội dung chưa có model ORM chung, nên ở đây khai báo bảng bằng SQLAlchemy Core với MetaData riêng
(không đưa vào Base.metadata để Alembic không coi là bảng mới). Chỉ khai các cột cần dùng.

Giả định cần nhóm xác nhận (#3, #11): "câu đã duyệt, dùng được" = questions.visibility = 'PUBLISHED'.
Đổi ở một chỗ: APPROVED_VISIBILITY.
"""
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Boolean, Column, ForeignKey, Integer, MetaData, String, Table, Text, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

APPROVED_VISIBILITY = "PUBLISHED"

content_metadata = MetaData()

chapters = Table(
    "chapters",
    content_metadata,
    Column("chapter_id", Integer, primary_key=True),
    Column("code", String(191)),
    Column("name", String(191)),
    Column("parent_chapter_id", Integer, ForeignKey("chapters.chapter_id")),
    Column("level", Integer),
)
questions = Table(
    "questions",
    content_metadata,
    Column("question_id", Integer, primary_key=True),
    Column("content", Text),
    Column("type", String(20)),
    Column("difficulty", String(4)),
    Column("grade", Integer),
    Column("visibility", String(10)),
)
questions_chapters = Table(
    "questions_chapters",
    content_metadata,
    Column("question_id", Integer, ForeignKey("questions.question_id"), primary_key=True),
    Column("chapter_id", Integer, ForeignKey("chapters.chapter_id"), primary_key=True),
)
statements = Table(
    "statements",
    content_metadata,
    Column("statement_id", Integer, primary_key=True),
    Column("content", Text),
    Column("question_id", Integer, ForeignKey("questions.question_id")),
    Column("is_correct", Boolean),
    Column("order", Integer),
)


def question_code(question_id: int) -> str:
    """Mã câu hiển thị, cùng dạng Q + 5 chữ số với data/question_bank.csv và script chấm #6."""
    return f"Q{question_id:05d}"


@dataclass
class PickResult:
    question_ids: list[int]
    available: int


class QuestionBankRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def chapter_names(self) -> dict[str, str]:
        rows = await self._session.execute(select(chapters.c.code, chapters.c.name).where(chapters.c.code.is_not(None)))
        return {code: name for code, name in rows.all()}

    def _pool(self, chapter_code: str, difficulty: str, exclude: Sequence[int]):
        parent = aliased(chapters)
        stmt = (
            select(questions.c.question_id)
            .join(questions_chapters, questions_chapters.c.question_id == questions.c.question_id)
            .join(chapters, chapters.c.chapter_id == questions_chapters.c.chapter_id)
            .outerjoin(parent, parent.c.chapter_id == chapters.c.parent_chapter_id)
            .where(
                questions.c.visibility == APPROVED_VISIBILITY,
                questions.c.difficulty == difficulty,
                or_(chapters.c.code == chapter_code, parent.c.code == chapter_code),
            )
            .distinct()
        )
        if exclude:
            stmt = stmt.where(questions.c.question_id.not_in(list(exclude)))
        return stmt

    async def pick(self, chapter_code: str, difficulty: str, n: int, exclude: Sequence[int] = ()) -> PickResult:
        """Chọn tối đa n câu đã duyệt thuộc chương (hoặc chương con) với độ khó cho trước, thứ tự ổn định."""
        pool = self._pool(chapter_code, difficulty, exclude).subquery()
        available = (await self._session.execute(select(func.count()).select_from(pool))).scalar_one()
        ids = (await self._session.execute(select(pool.c.question_id).order_by(pool.c.question_id).limit(n))).scalars()
        return PickResult(question_ids=list(ids), available=available)

    async def load_items(self, question_ids: Sequence[int]) -> dict[int, dict]:
        """Nội dung câu và lựa chọn để hiển thị. KHÔNG đọc đáp án, lời giải hay cờ đúng/sai."""
        if not question_ids:
            return {}
        rows = await self._session.execute(
            select(questions.c.question_id, questions.c.content, questions.c.type, questions.c.difficulty).where(
                and_(questions.c.question_id.in_(list(question_ids)), questions.c.visibility == APPROVED_VISIBILITY)
            )
        )
        items = {
            qid: {"question_id": qid, "code": question_code(qid), "content": content, "type": qtype,
                  "difficulty": diff, "statements": []}
            for qid, content, qtype, diff in rows.all()
        }
        st = await self._session.execute(
            select(statements.c.question_id, statements.c.content, statements.c.order)
            .where(statements.c.question_id.in_(list(items)))
            .order_by(statements.c.question_id, statements.c.order, statements.c.statement_id)
        )
        for qid, content, order in st.all():
            items[qid]["statements"].append({"order": order, "content": content})
        return items
