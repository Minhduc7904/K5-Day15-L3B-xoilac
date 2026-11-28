"""Đọc ngân hàng câu hỏi nền (bảng tạo ở migration 0002) cho pipeline học sinh (#4). Chỉ đọc.

Các bảng nội dung chưa có model ORM chung, nên ở đây khai báo bảng bằng SQLAlchemy Core với MetaData riêng
(không đưa vào Base.metadata để Alembic không coi là bảng mới). Chỉ khai các cột cần dùng.

"Câu khả dụng" (#3, #11): questions.visibility = 'PUBLISHED' và chưa lưu trữ (questions.archived_at IS NULL,
migration 0021). Mọi truy vấn chọn câu cho đề mới dùng chung `available_questions()`; đổi định nghĩa ở một chỗ.
Đọc lại câu đã nằm trong đề (load_items, load_grading_keys) không lọc archived để đề và lịch sử cũ vẫn đọc được.
"""
import re
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, Text, and_, func, or_, select,
)
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
    Column("slug", String(191)),
    Column("subject_id", Integer),
    Column("order_in_parent", Integer),
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
    Column("searchable_content", Text),
    Column("slug", String(255)),
    Column("subject_id", Integer),
    Column("archived_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
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
questions_exams = Table(
    "questions_exams",
    content_metadata,
    Column("question_id", Integer, ForeignKey("questions.question_id"), primary_key=True),
    Column("exam_id", Integer, primary_key=True),
    Column("order", Integer),
)
subjects = Table(
    "subjects",
    content_metadata,
    Column("subject_id", Integer, primary_key=True),
    Column("name", String(191)),
    Column("code", String(191)),
)


def available_questions():
    """Điều kiện SQL "câu khả dụng để dựng đề mới": đã đăng (PUBLISHED) và chưa lưu trữ.

    Dùng chung cho pipeline #4 (`_pool`) và bộ lọc trạng thái của API admin #11."""
    return and_(questions.c.visibility == APPROVED_VISIBILITY, questions.c.archived_at.is_(None))


_GRADE_PREFIX = re.compile(r"^(\d{1,2})C")


def grade_of(chapter_code: str) -> int | None:
    """Khối lớp từ tiền tố mã chương (`12C11` → 12). Mã không theo dạng này trả None."""
    match = _GRADE_PREFIX.match(chapter_code)
    return int(match.group(1)) if match else None


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

    async def chapter_catalog(self) -> dict[str, dict[str, str | int | None]]:
        """Mã chương → tên, mã chương cha và khối lớp (suy từ tiền tố mã, vd `12C11` → 12)."""
        parent = chapters.alias("chapter_parent")
        query = (select(chapters.c.code, chapters.c.name, parent.c.code)
                 .outerjoin(parent, parent.c.chapter_id == chapters.c.parent_chapter_id)
                 .where(chapters.c.code.is_not(None)).order_by(chapters.c.chapter_id))
        return {code: {"name": name, "parent_code": parent_code, "grade": grade_of(code)}
                for code, name, parent_code in (await self._session.execute(query)).all()}

    def _pool(
        self,
        *,
        chapter_codes: Sequence[str] | None,
        difficulty: str | None,
        question_type: str | None,
        grade: int | None,
        exclude: Sequence[int],
        difficulties: Sequence[str] | None = None,
    ):
        """Truy vấn mã các câu đã duyệt thoả điều kiện. Điều kiện None là không lọc theo điều kiện đó."""
        stmt = select(questions.c.question_id).where(available_questions())
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
        if difficulties:
            stmt = stmt.where(questions.c.difficulty.in_(list(difficulties)))
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

    async def practice_capacity(
        self, chapter_codes: Sequence[str], difficulties: Sequence[str], types: Sequence[str],
    ) -> tuple[list[dict], int]:
        """Đếm theo ô của ma trận và đếm số câu phân biệt trên toàn phạm vi."""
        if not chapter_codes:
            return [], 0
        approved = self._pool(chapter_codes=chapter_codes, difficulty=None, question_type=None,
                              grade=None, exclude=()).subquery()
        parent = chapters.alias("practice_parent")
        query = (
            select(chapters.c.code, parent.c.code, questions.c.difficulty, questions.c.type, questions.c.question_id)
            .select_from(questions.join(approved, approved.c.question_id == questions.c.question_id)
                         .join(questions_chapters, questions_chapters.c.question_id == questions.c.question_id)
                         .join(chapters, chapters.c.chapter_id == questions_chapters.c.chapter_id)
                         .outerjoin(parent, parent.c.chapter_id == chapters.c.parent_chapter_id))
            .where(or_(chapters.c.code.in_(chapter_codes), parent.c.code.in_(chapter_codes)),
                   questions.c.difficulty.in_(difficulties), questions.c.type.in_(types))
        )
        cells: dict[tuple[str, str, str], set[int]] = {}
        scope = set(chapter_codes)
        ids = set()
        for code, parent_code, difficulty, kind, question_id in (await self._session.execute(query)).all():
            for match in {code, parent_code} & scope:
                cells.setdefault((match, difficulty, kind), set()).add(question_id)
            ids.add(question_id)
        return [
            {"chapter_code": code, "difficulty": difficulty, "type": kind, "available": len(available)}
            for (code, difficulty, kind), available in sorted(cells.items())
        ], len(ids)

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
        difficulties: Sequence[str] | None = None,
    ) -> PickResult:
        """Chọn câu cho một phần của mẫu kỳ thi: đúng loại câu, trong các chương cho phép, đúng mức độ khó.

        Mẫu không giới hạn chương thì lọc theo khối (questions.grade) nếu mẫu có khối. `difficulties` giới hạn thêm
        trong tập mức khó cho phép khi không chọn một mức cụ thể (dùng để bù câu thiếu)."""
        return await self._pick(n, chapter_codes=chapter_codes, difficulty=difficulty, question_type=question_type,
                                grade=None if chapter_codes else grade, exclude=exclude,
                                prefer_subchapters=prefer_subchapters, difficulties=difficulties)

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
