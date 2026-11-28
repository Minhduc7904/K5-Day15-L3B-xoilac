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
    Column("correct_answer", Text),
    Column("solution", Text),
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

    async def chapter_catalog(self) -> dict[str, dict[str, str | None]]:
        parent = chapters.alias("chapter_parent")
        query = (select(chapters.c.code, chapters.c.name, parent.c.code)
                 .outerjoin(parent, parent.c.chapter_id == chapters.c.parent_chapter_id)
                 .where(chapters.c.code.is_not(None)).order_by(chapters.c.chapter_id))
        return {code: {"name": name, "parent_code": parent_code}
                for code, name, parent_code in (await self._session.execute(query)).all()}

    def _pool(
        self,
        *,
        chapter_codes: Sequence[str] | None,
        difficulty: str | None,
        question_type: str | None,
        grade: int | None,
        exclude: Sequence[int],
    ):
        """Truy vấn mã các câu đã duyệt thoả điều kiện. Điều kiện None là không lọc theo điều kiện đó."""
        stmt = select(questions.c.question_id).where(questions.c.visibility == APPROVED_VISIBILITY)
        if chapter_codes:
            parent = aliased(chapters)
            codes = list(chapter_codes)
            stmt = (
                stmt.join(questions_chapters, questions_chapters.c.question_id == questions.c.question_id)
                .join(chapters, chapters.c.chapter_id == questions_chapters.c.chapter_id)
                .outerjoin(parent, parent.c.chapter_id == chapters.c.parent_chapter_id)
                .where(or_(chapters.c.code.in_(codes), parent.c.code.in_(codes)))
            )
        if difficulty is not None:
            stmt = stmt.where(questions.c.difficulty == difficulty)
        if question_type is not None:
            stmt = stmt.where(questions.c.type == question_type)
        if grade is not None:
            stmt = stmt.where(questions.c.grade == grade)
        if exclude:
            stmt = stmt.where(questions.c.question_id.not_in(list(exclude)))
        return stmt.distinct()

    async def _pick(self, n: int, *, prefer_subchapters: bool = False, **filters) -> PickResult:
        pool = self._pool(**filters).subquery()
        available = (await self._session.execute(select(func.count()).select_from(pool))).scalar_one()
        query = select(pool.c.question_id)
        if prefer_subchapters:
            parent = chapters.alias("preferred_parent")
            linked = (select(1).select_from(questions_chapters
                      .join(chapters, chapters.c.chapter_id == questions_chapters.c.chapter_id)
                      .outerjoin(parent, parent.c.chapter_id == chapters.c.parent_chapter_id))
                      .where(questions_chapters.c.question_id == pool.c.question_id,
                             chapters.c.parent_chapter_id.is_not(None)))
            if filters["chapter_codes"]:
                codes = list(filters["chapter_codes"])
                linked = linked.where(or_(chapters.c.code.in_(codes), parent.c.code.in_(codes)))
            query = query.order_by(linked.correlate(pool).exists().desc())
        ids = (await self._session.execute(query.order_by(pool.c.question_id).limit(n))).scalars()
        return PickResult(question_ids=list(ids), available=available)

    async def pick(self, chapter_code: str, difficulty: str, n: int, exclude: Sequence[int] = ()) -> PickResult:
        """Chọn tối đa n câu đã duyệt thuộc chương (hoặc chương con) với độ khó cho trước, thứ tự ổn định."""
        return await self._pick(n, chapter_codes=[chapter_code], difficulty=difficulty, question_type=None,
                                grade=None, exclude=exclude)

    async def pick_for_section(
        self,
        *,
        question_type: str,
        n: int,
        chapter_codes: Sequence[str] | None = None,
        difficulty: str | None = None,
        grade: int | None = None,
        exclude: Sequence[int] = (),
        prefer_subchapters: bool = False,
    ) -> PickResult:
        """Chọn câu cho một phần của mẫu kỳ thi: đúng loại câu, trong các chương cho phép, đúng mức độ khó.

        Mẫu không giới hạn chương thì lọc theo khối (questions.grade) nếu mẫu có khối."""
        return await self._pick(n, chapter_codes=chapter_codes, difficulty=difficulty, question_type=question_type,
                                grade=None if chapter_codes else grade, exclude=exclude, prefer_subchapters=prefer_subchapters)

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
                  "difficulty": diff, "chapter_codes": [], "subchapter_codes": [], "statements": []}
            for qid, content, qtype, diff in rows.all()
        }
        if not items:
            return {}
        # Chương gốc của câu (câu gắn chương con thì lấy mã chương cha), để đề theo mẫu hiển thị được chương.
        parent = aliased(chapters)
        ch = await self._session.execute(
            select(questions_chapters.c.question_id, func.coalesce(parent.c.code, chapters.c.code),
                   chapters.c.code, parent.c.code)
            .join(chapters, chapters.c.chapter_id == questions_chapters.c.chapter_id)
            .outerjoin(parent, parent.c.chapter_id == chapters.c.parent_chapter_id)
            .where(questions_chapters.c.question_id.in_(list(items)))
            .order_by(questions_chapters.c.question_id, chapters.c.chapter_id)
        )
        for qid, code, leaf_code, parent_code in ch.all():
            if code and code not in items[qid]["chapter_codes"]:
                items[qid]["chapter_codes"].append(code)
            if parent_code and leaf_code and leaf_code not in items[qid]["subchapter_codes"]:
                items[qid]["subchapter_codes"].append(leaf_code)
        st = await self._session.execute(
            select(statements.c.question_id, statements.c.content, statements.c.order, statements.c.statement_id)
            .where(statements.c.question_id.in_(list(items)))
            .order_by(statements.c.question_id, statements.c.order, statements.c.statement_id)
        )
        for qid, content, order, statement_id in st.all():
            items[qid]["statements"].append({"order": order, "content": content, "statement_id": statement_id})
        return items

    async def load_grading_keys(self, ids: list[int]) -> dict:
        rows = await self._session.execute(
            select(questions.c.question_id, questions.c.correct_answer, questions.c.solution)
            .where(questions.c.question_id.in_(ids), questions.c.visibility == APPROVED_VISIBILITY)
        )
        keys = {qid: {"answer": answer, "solution": solution, "options": {}} for qid, answer, solution in rows}
        options = await self._session.execute(
            select(statements.c.question_id, statements.c.statement_id, statements.c.content, statements.c.is_correct)
            .where(statements.c.question_id.in_(keys))
            .order_by(statements.c.order, statements.c.statement_id)
        )
        for qid, option_id, content, correct in options:
            keys[qid]["options"][option_id] = (content, correct)
        return keys
