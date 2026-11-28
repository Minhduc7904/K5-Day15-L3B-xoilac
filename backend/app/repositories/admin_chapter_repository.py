"""Đọc/ghi danh mục chương cho admin (#11). Bảng chapters do migration 0002 tạo; khai Core ở question_bank_repository."""
from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_question_repository import descendants_cte
from app.repositories.question_bank_repository import chapters, questions_chapters, subjects

CHAPTER_COLUMNS = (
    chapters.c.chapter_id, chapters.c.code, chapters.c.name, chapters.c.slug, chapters.c.parent_chapter_id,
    chapters.c.order_in_parent, chapters.c.level, chapters.c.subject_id,
)


class AdminChapterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def all_chapters(self) -> list[dict]:
        rows = await self._session.execute(select(*CHAPTER_COLUMNS).order_by(
            chapters.c.order_in_parent, chapters.c.chapter_id))
        return [dict(r) for r in rows.mappings().all()]

    async def links(self) -> list[tuple[int, int]]:
        """(chapter_id, question_id) của mọi liên kết câu–chương."""
        rows = await self._session.execute(select(questions_chapters.c.chapter_id, questions_chapters.c.question_id))
        return [tuple(r) for r in rows.all()]

    async def get(self, chapter_id: int) -> dict | None:
        row = (await self._session.execute(select(*CHAPTER_COLUMNS).where(chapters.c.chapter_id == chapter_id))
               ).mappings().one_or_none()
        return dict(row) if row else None

    async def taken(self, code: str, slug: str, exclude_id: int | None) -> dict[str, bool]:
        stmt = select(chapters.c.code, chapters.c.slug).where(or_(chapters.c.code == code, chapters.c.slug == slug))
        if exclude_id is not None:
            stmt = stmt.where(chapters.c.chapter_id != exclude_id)
        rows = (await self._session.execute(stmt)).all()
        return {"code": any(r[0] == code for r in rows), "slug": any(r[1] == slug for r in rows)}

    async def subtree_ids(self, chapter_id: int) -> list[int]:
        """Chương và mọi chương con cháu (WITH RECURSIVE)."""
        tree = descendants_cte(chapter_id, "subtree")
        return list((await self._session.execute(select(tree.c.chapter_id))).scalars())

    async def usage(self, chapter_ids: list[int]) -> tuple[int, int]:
        """(số chương con trực tiếp của chương đầu, số câu phân biệt gắn vào các chương này)."""
        children = (await self._session.execute(
            select(func.count()).where(chapters.c.parent_chapter_id == chapter_ids[0]))).scalar_one()
        questions = (await self._session.execute(
            select(func.count(func.distinct(questions_chapters.c.question_id)))
            .where(questions_chapters.c.chapter_id.in_(chapter_ids)))).scalar_one()
        return children, questions

    async def next_order(self, parent_id: int | None) -> int:
        cond = chapters.c.parent_chapter_id.is_(None) if parent_id is None else chapters.c.parent_chapter_id == parent_id
        current = (await self._session.execute(select(func.max(chapters.c.order_in_parent)).where(cond))).scalar_one()
        return (current or 0) + 1

    async def default_subject(self, grade_prefix: str) -> int | None:
        """Môn của các chương gốc cùng khối (vd tiền tố `12C`), nếu không có thì môn đầu tiên."""
        found = (await self._session.execute(
            select(chapters.c.subject_id).where(chapters.c.parent_chapter_id.is_(None),
                                                chapters.c.code.like(f"{grade_prefix}%")).limit(1))).scalar()
        if found is not None:
            return found
        return (await self._session.execute(select(subjects.c.subject_id).order_by(subjects.c.subject_id).limit(1))
                ).scalar()

    async def insert(self, values: dict) -> int:
        return (await self._session.execute(insert(chapters).values(**values).returning(chapters.c.chapter_id))
                ).scalar_one()

    async def update(self, chapter_id: int, values: dict) -> None:
        await self._session.execute(update(chapters).where(chapters.c.chapter_id == chapter_id).values(**values))

    async def shift_levels(self, chapter_ids: list[int], delta: int) -> None:
        if delta and chapter_ids:
            await self._session.execute(update(chapters).where(chapters.c.chapter_id.in_(chapter_ids))
                                        .values(level=chapters.c.level + delta))

    async def delete(self, chapter_id: int) -> None:
        await self._session.execute(delete(chapters).where(chapters.c.chapter_id == chapter_id))
