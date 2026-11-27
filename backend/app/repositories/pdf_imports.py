from sqlalchemy import column, insert, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pdf_import import PdfDraft, PdfImport

# Migration 0002 owns these tables. These projections share its columns with Issues #4 and #11.
media = table(
    "media", *(column(name) for name in (
        "media_id", "file_name", "original_name", "mime_type", "file_size",
        "type", "status", "bucket_name", "object_key", "parent_id",
    ))
)
questions = table(
    "questions", *(column(name) for name in (
        "question_id", "content", "slug", "type", "correct_answer", "solution",
        "difficulty", "grade", "subject_id", "visibility",
    ))
)
statements = table(
    "statements", *(column(name) for name in ("statement_id", "question_id", "content", "is_correct", "order"))
)
chapters = table(
    "chapters", *(column(name) for name in ("chapter_id", "code", "subject_id", "parent_chapter_id", "level"))
)
question_chapters = table("questions_chapters", column("question_id"), column("chapter_id"))


class PdfImportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_import(self, **values) -> PdfImport:
        row = PdfImport(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_import(self, import_id: int) -> PdfImport | None:
        return await self.session.get(PdfImport, import_id)

    async def list_imports(self, offset: int, limit: int) -> list[PdfImport]:
        query = select(PdfImport).order_by(PdfImport.id.desc()).offset(offset).limit(limit)
        return list((await self.session.scalars(query)).all())

    async def get_drafts(self, import_id: int) -> list[PdfDraft]:
        query = select(PdfDraft).where(PdfDraft.import_id == import_id).order_by(PdfDraft.position)
        return list((await self.session.scalars(query)).all())

    async def get_draft(self, import_id: int, draft_id: int, *, lock: bool = False) -> PdfDraft | None:
        query = select(PdfDraft).where(PdfDraft.import_id == import_id, PdfDraft.id == draft_id)
        return await self.session.scalar(query.with_for_update() if lock else query)

    def add_draft(self, import_id: int, position: int, payload: dict) -> None:
        self.session.add(PdfDraft(import_id=import_id, position=position, payload=payload))

    async def add_media(self, **values) -> int:
        return (await self.session.execute(insert(media).values(**values).returning(media.c.media_id))).scalar_one()

    async def get_media(self, original_id: int, media_id: int):
        query = select(media).where(
            media.c.media_id == media_id,
            (media.c.parent_id == original_id) | (media.c.media_id == original_id),
        )
        return (await self.session.execute(query)).mappings().one_or_none()

    async def get_chapters(self, codes: list[str]):
        query = select(chapters).where(chapters.c.code.in_(codes))
        return (await self.session.execute(query)).mappings().all()

    async def publish(self, fields: dict, options: list[dict], chapter_ids: list[int]) -> int:
        question_id = (await self.session.execute(
            insert(questions).values(**fields, visibility="PUBLISHED").returning(questions.c.question_id)
        )).scalar_one()
        if options:
            await self.session.execute(insert(statements), [
                {"question_id": question_id, "content": option["content"],
                 "is_correct": option["isCorrect"], "order": index}
                for index, option in enumerate(options, 1)
            ])
        await self.session.execute(insert(question_chapters), [
            {"question_id": question_id, "chapter_id": chapter_id} for chapter_id in chapter_ids
        ])
        return question_id

    async def read_published_question(self, question_id: int) -> dict | None:
        """Student-safe projection for the shared bank handoff."""
        question = (await self.session.execute(
            select(questions.c.question_id, questions.c.content, questions.c.type, questions.c.difficulty,
                   questions.c.grade).where(questions.c.question_id == question_id, questions.c.visibility == "PUBLISHED")
        )).mappings().one_or_none()
        if question is None:
            return None
        options = (await self.session.execute(
            select(statements.c.content, statements.c.order).where(statements.c.question_id == question_id)
            .order_by(statements.c.order, statements.c.statement_id)
        )).mappings().all()
        return {**question, "statements": [dict(option) for option in options]}
