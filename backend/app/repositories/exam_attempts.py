from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam_attempt import ExamAttempt, ExamAttemptMutation
from app.models.exam_chat import ExamChatSession, ExamDraft
from app.repositories.pdf_imports import media


class ExamAttemptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def clock(self) -> datetime:
        if self.session.get_bind().dialect.name == "postgresql":
            return await self.session.scalar(select(func.clock_timestamp()))
        return datetime.now(UTC)

    async def draft(self, user_id: int, draft_id: int, *, lock: bool = False) -> ExamDraft | None:
        query = select(ExamDraft).join(ExamChatSession).where(
            ExamDraft.draft_id == draft_id, ExamChatSession.user_id == user_id, ExamDraft.is_current
        )
        return await self.session.scalar(query.with_for_update(of=ExamDraft) if lock else query)

    async def latest(self, user_id: int, draft_id: int) -> ExamAttempt | None:
        return await self.session.scalar(
            select(ExamAttempt).where(ExamAttempt.user_id == user_id, ExamAttempt.draft_id == draft_id)
            .order_by(ExamAttempt.attempt_id.desc()).limit(1).with_for_update()
        )

    async def get(self, attempt_id: int, user_id: int | None = None, *, lock=True) -> ExamAttempt | None:
        query = select(ExamAttempt).where(ExamAttempt.attempt_id == attempt_id)
        if user_id is not None:
            query = query.where(ExamAttempt.user_id == user_id)
        return await self.session.scalar(query.with_for_update() if lock else query)

    async def history(self, user_id: int, draft_id: int) -> list[ExamAttempt]:
        return list(await self.session.scalars(
            select(ExamAttempt).where(ExamAttempt.user_id == user_id, ExamAttempt.draft_id == draft_id,
                                      ExamAttempt.status == "graded")
            .order_by(ExamAttempt.attempt_id.desc())
        ))

    async def summaries(self, user_id: int):
        return (await self.session.execute(
            select(ExamAttempt.draft_id, ExamAttempt.status, ExamAttempt.deadline_at, ExamAttempt.finished_at,
                   ExamAttempt.result["score"].as_float())
            .where(ExamAttempt.user_id == user_id)
            .order_by(ExamAttempt.attempt_id.desc())
        )).all()

    async def graded(self, user_id: int, limit: int, *, by_grading_time: bool = False) -> list[ExamAttempt]:
        """Các lượt đã chấm gần nhất của học sinh, dùng cho dashboard và lịch sử của agent."""
        order = [ExamAttempt.attempt_id.desc()]
        if by_grading_time:
            graded_at = func.coalesce(ExamAttempt.graded_at, ExamAttempt.finished_at, ExamAttempt.started_at)
            order.insert(0, graded_at.desc())
        return list(await self.session.scalars(
            select(ExamAttempt).where(ExamAttempt.user_id == user_id, ExamAttempt.status == "graded")
            .order_by(*order).limit(limit)
        ))

    async def due_ids(self, now: datetime) -> list[int]:
        return list(await self.session.scalars(
            select(ExamAttempt.attempt_id)
            .where(ExamAttempt.status == "in_progress", ExamAttempt.deadline_at <= now)
            .order_by(ExamAttempt.deadline_at).limit(100)
        ))

    async def revisions(self, ids: list[int]):
        return (await self.session.execute(
            select(ExamAttempt.attempt_id, ExamAttempt.revision, ExamAttempt.reason)
            .where(ExamAttempt.attempt_id.in_(ids))
        )).all()

    async def media_key(self, media_id: int) -> str | None:
        return await self.session.scalar(select(media.c.object_key).where(media.c.media_id == media_id))

    async def has_mutation(self, attempt_id: int, mutation_id: str) -> bool:
        return await self.session.get(ExamAttemptMutation, (attempt_id, mutation_id)) is not None

    def remember_mutation(self, attempt_id: int, mutation_id: str) -> None:
        self.session.add(ExamAttemptMutation(attempt_id=attempt_id, mutation_id=mutation_id))

    async def insert(self, **values) -> ExamAttempt:
        attempt = ExamAttempt(**values)
        self.session.add(attempt)
        await self.session.flush()
        return attempt

    async def commit(self):
        await self.session.commit()
