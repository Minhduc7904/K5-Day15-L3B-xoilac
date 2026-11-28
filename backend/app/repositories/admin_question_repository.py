"""Đọc/ghi ngân hàng câu hỏi cho admin (#11). Dùng chung bảng Core và `available_questions()` với #4.

Không xoá cứng câu: lưu trữ = đặt questions.archived_at. Lựa chọn/mệnh đề sửa tại chỗ theo statement_id
để đề nháp đã tham chiếu id cũ vẫn chấm được.
"""
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.pdf_imports import media
from app.repositories.question_bank_repository import (
    APPROVED_VISIBILITY, chapters, questions, questions_chapters, questions_exams, statements,
)

SUMMARY_COLUMNS = (
    questions.c.question_id, questions.c.content, questions.c.type, questions.c.difficulty, questions.c.grade,
    questions.c.visibility, questions.c.archived_at, questions.c.updated_at,
)


def descendants_cte(chapter_id: int, name: str = "chapter_tree"):
    """CTE đệ quy: chương `chapter_id` và mọi chương con cháu (cột chapter_id)."""
    tree = select(chapters.c.chapter_id).where(chapters.c.chapter_id == chapter_id).cte(name, recursive=True)
    return tree.union_all(select(chapters.c.chapter_id).where(chapters.c.parent_chapter_id == tree.c.chapter_id))


class AdminQuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    # ---- đọc --------------------------------------------------------------------------------------------

    def _filtered(self, *, q: str | None, grade: int | None, chapter_id: int | None, qtype: str | None,
                  difficulty: str | None, status: str | None, question_id: int | None):
        stmt = select(questions.c.question_id)
        if q:
            pattern = f"%{q}%"
            text = func.coalesce(questions.c.searchable_content, questions.c.content)
            match = text.ilike(pattern)
            stmt = stmt.where(or_(match, questions.c.question_id == question_id) if question_id else match)
        if grade is not None:
            stmt = stmt.where(questions.c.grade == grade)
        if qtype:
            stmt = stmt.where(questions.c.type == qtype)
        if difficulty:
            stmt = stmt.where(questions.c.difficulty == difficulty)
        if status == "ARCHIVED":
            stmt = stmt.where(questions.c.archived_at.is_not(None))
        elif status:
            stmt = stmt.where(questions.c.visibility == status, questions.c.archived_at.is_(None))
        if chapter_id is not None:
            tree = descendants_cte(chapter_id)
            linked = select(questions_chapters.c.question_id).where(
                questions_chapters.c.chapter_id.in_(select(tree.c.chapter_id)))
            stmt = stmt.where(questions.c.question_id.in_(linked))
        return stmt

    async def search(self, *, page: int, page_size: int, **filters) -> tuple[list[dict], int]:
        ids = self._filtered(**filters).subquery()
        total = (await self._session.execute(select(func.count()).select_from(ids))).scalar_one()
        rows = await self._session.execute(
            select(*SUMMARY_COLUMNS).where(questions.c.question_id.in_(select(ids.c.question_id)))
            .order_by(questions.c.question_id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        items = [dict(r) for r in rows.mappings().all()]
        await self._attach_chapters(items)
        return items, total

    async def _attach_chapters(self, items: list[dict]) -> None:
        by_id = {item["question_id"]: item for item in items}
        for item in items:
            item["chapters"] = []
        if not by_id:
            return
        rows = await self._session.execute(
            select(questions_chapters.c.question_id, chapters.c.chapter_id, chapters.c.code, chapters.c.name)
            .join(chapters, chapters.c.chapter_id == questions_chapters.c.chapter_id)
            .where(questions_chapters.c.question_id.in_(list(by_id)))
            .order_by(questions_chapters.c.question_id, chapters.c.chapter_id)
        )
        for qid, chapter_id, code, name in rows.all():
            by_id[qid]["chapters"].append({"chapter_id": chapter_id, "code": code, "name": name})

    async def get(self, question_id: int) -> dict | None:
        row = (await self._session.execute(
            select(*SUMMARY_COLUMNS, questions.c.correct_answer, questions.c.solution, questions.c.created_at)
            .where(questions.c.question_id == question_id)
        )).mappings().one_or_none()
        if row is None:
            return None
        item = dict(row)
        await self._attach_chapters([item])
        st = await self._session.execute(
            select(statements.c.statement_id, statements.c.content, statements.c.is_correct, statements.c.order)
            .where(statements.c.question_id == question_id)
            .order_by(statements.c.order, statements.c.statement_id)
        )
        item["statements"] = [dict(r) for r in st.mappings().all()]
        item["exam_count"] = (await self._session.execute(
            select(func.count(func.distinct(questions_exams.c.exam_id)))
            .where(questions_exams.c.question_id == question_id)
        )).scalar_one()
        return item

    async def chapters_by_ids(self, chapter_ids: Sequence[int]) -> list[dict]:
        rows = await self._session.execute(
            select(chapters.c.chapter_id, chapters.c.code, chapters.c.subject_id, chapters.c.parent_chapter_id)
            .where(chapters.c.chapter_id.in_(list(chapter_ids)))
        )
        return [dict(r) for r in rows.mappings().all()]

    async def root_codes(self, chapter_ids: Sequence[int]) -> dict[int, str | None]:
        """Mã chương gốc (cấp 0) của từng chương, để suy khối lớp."""
        result: dict[int, str | None] = {}
        for chapter_id in chapter_ids:
            current, code = chapter_id, None
            for _ in range(20):  # cây chương sâu tối đa vài cấp; chặn vòng lặp nếu dữ liệu hỏng
                row = (await self._session.execute(
                    select(chapters.c.code, chapters.c.parent_chapter_id).where(chapters.c.chapter_id == current)
                )).one_or_none()
                if row is None:
                    break
                code, parent = row
                if parent is None:
                    break
                current = parent
            result[chapter_id] = code
        return result

    async def existing_statement_ids(self, question_id: int) -> set[int]:
        rows = await self._session.execute(
            select(statements.c.statement_id).where(statements.c.question_id == question_id))
        return set(rows.scalars())

    async def ready_images(self, media_ids: Sequence[int]) -> set[int]:
        if not media_ids:
            return set()
        rows = await self._session.execute(
            select(media.c.media_id).where(media.c.media_id.in_(list(media_ids)), media.c.type == "IMAGE",
                                           media.c.status == "READY"))
        return set(rows.scalars())

    async def image(self, media_id: int) -> dict | None:
        row = (await self._session.execute(
            select(media.c.object_key, media.c.mime_type, media.c.type, media.c.status)
            .where(media.c.media_id == media_id)
        )).mappings().one_or_none()
        return dict(row) if row and row["type"] == "IMAGE" and row["status"] == "READY" else None

    async def is_available(self, question_id: int) -> bool:
        row = (await self._session.execute(
            select(questions.c.visibility, questions.c.archived_at).where(questions.c.question_id == question_id)
        )).one_or_none()
        return bool(row) and row[0] == APPROVED_VISIBILITY and row[1] is None

    # ---- ghi --------------------------------------------------------------------------------------------

    async def insert_question(self, fields: dict) -> int:
        return (await self._session.execute(
            insert(questions).values(**fields).returning(questions.c.question_id))).scalar_one()

    async def update_question(self, question_id: int, fields: dict) -> None:
        await self._session.execute(update(questions).where(questions.c.question_id == question_id).values(**fields))

    async def replace_statements(self, question_id: int, items: list[dict]) -> None:
        """items: [{statement_id|None, content, is_correct, order}]. Id cũ không còn trong items thì xoá."""
        keep = {item["statement_id"] for item in items if item.get("statement_id")}
        stale = delete(statements).where(statements.c.question_id == question_id)
        if keep:
            stale = stale.where(statements.c.statement_id.not_in(list(keep)))
        await self._session.execute(stale)
        for item in items:
            values = {"content": item["content"], "is_correct": item["is_correct"], "order": item["order"]}
            if item.get("statement_id"):
                await self._session.execute(update(statements).where(
                    statements.c.statement_id == item["statement_id"]).values(**values))
            else:
                await self._session.execute(insert(statements).values(question_id=question_id, **values))

    async def replace_chapters(self, question_id: int, chapter_ids: Sequence[int]) -> None:
        await self._session.execute(delete(questions_chapters).where(questions_chapters.c.question_id == question_id))
        await self._session.execute(insert(questions_chapters), [
            {"question_id": question_id, "chapter_id": chapter_id} for chapter_id in chapter_ids])

    async def set_archived(self, question_id: int, archived_at: datetime | None) -> None:
        await self._session.execute(update(questions).where(questions.c.question_id == question_id)
                                    .values(archived_at=archived_at, updated_at=func.now()))

    async def add_image(self, **values) -> int:
        return (await self._session.execute(insert(media).values(**values).returning(media.c.media_id))).scalar_one()
