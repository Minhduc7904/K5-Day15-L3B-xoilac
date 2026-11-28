"""Truy vấn đọc cho dashboard thống kê của admin. Chỉ đọc, chỉ trả số liệu thô (không có email hay tên).

Phép nhóm theo ngày/tuần làm ở use case bằng Python (múi giờ Việt Nam, chạy được trên cả SQLite lẫn PostgreSQL);
ở đây mọi truy vấn đều bị chặn theo mốc thời gian hoặc nhóm bằng SQL, nên số dòng nhỏ.
"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam_attempt import ExamAttempt
from app.models.exam_chat import ExamChatSession, ExamDraft
from app.models.pdf_import import PdfDraft, PdfImport
from app.models.session import UserSession
from app.models.student import CreditLedger, StudentProfile
from app.models.user import ROLE_STUDENT, User
from app.repositories.question_bank_repository import chapters, questions, questions_chapters

# Giới hạn số lượt làm bài đọc để tính điểm/chương: đủ cho vài tháng dữ liệu, chặn truy vấn phình to.
ATTEMPT_LIMIT = 5000


class AdminAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ---- học sinh ---------------------------------------------------------------------------------------

    async def students_created(self, since: datetime) -> list[tuple[int, datetime, datetime | None]]:
        rows = await self._session.execute(
            select(User.user_id, User.created_at, User.email_verified_at)
            .where(User.role == ROLE_STUDENT, User.created_at >= since)
        )
        return [tuple(r) for r in rows.all()]

    async def student_count(self) -> int:
        return (await self._session.execute(
            select(func.count()).select_from(User).where(User.role == ROLE_STUDENT))).scalar_one()

    async def logins(self, since: datetime) -> list[tuple[int, datetime]]:
        rows = await self._session.execute(
            select(UserSession.user_id, UserSession.created_at)
            .join(User, User.user_id == UserSession.user_id)
            .where(User.role == ROLE_STUDENT, UserSession.created_at >= since)
        )
        return [tuple(r) for r in rows.all()]

    async def profile_user_ids(self) -> set[int]:
        return set((await self._session.execute(select(StudentProfile.user_id))).scalars())

    async def profile_mix(self) -> list[tuple[int, int]]:
        rows = await self._session.execute(select(StudentProfile.grade, StudentProfile.target_score))
        return [tuple(r) for r in rows.all()]

    async def draft_owner_ids(self) -> set[int]:
        rows = await self._session.execute(
            select(ExamChatSession.user_id).join(ExamDraft, ExamDraft.session_id == ExamChatSession.session_id)
            .where(ExamChatSession.user_id.is_not(None)).distinct())
        return set(rows.scalars())

    async def attempt_owner_ids(self) -> set[int]:
        return set((await self._session.execute(select(ExamAttempt.user_id).distinct())).scalars())

    # ---- bài làm ----------------------------------------------------------------------------------------

    async def attempts(self, since: datetime) -> list[dict]:
        rows = await self._session.execute(
            select(ExamAttempt.attempt_id, ExamAttempt.user_id, ExamAttempt.draft_id, ExamAttempt.started_at,
                   ExamAttempt.finished_at, ExamAttempt.status, ExamAttempt.reason, ExamAttempt.snapshot,
                   ExamAttempt.result)
            .where(ExamAttempt.started_at >= since)
            .order_by(ExamAttempt.started_at.desc()).limit(ATTEMPT_LIMIT)
        )
        return [dict(r) for r in rows.mappings().all()]

    # ---- ngân hàng câu hỏi ------------------------------------------------------------------------------

    async def question_groups(self) -> list[tuple[str | None, bool, str | None, int | None, str | None, int]]:
        """(visibility, đã lưu trữ?, loại, khối, độ khó, số câu)."""
        archived = questions.c.archived_at.is_not(None)
        rows = await self._session.execute(
            select(questions.c.visibility, archived, questions.c.type, questions.c.grade, questions.c.difficulty,
                   func.count())
            .group_by(questions.c.visibility, archived, questions.c.type, questions.c.grade, questions.c.difficulty)
        )
        return [tuple(r) for r in rows.all()]

    async def coverage(self) -> list[tuple[int, str | None, str | None, str | None]]:
        """Mỗi câu khả dụng gắn với từng chương: (question_id, độ khó, mã chương, mã chương cha)."""
        parent = chapters.alias("chapter_parent")
        rows = await self._session.execute(
            select(questions.c.question_id, questions.c.difficulty, chapters.c.code, parent.c.code)
            .join(questions_chapters, questions_chapters.c.question_id == questions.c.question_id)
            .join(chapters, chapters.c.chapter_id == questions_chapters.c.chapter_id)
            .outerjoin(parent, parent.c.chapter_id == chapters.c.parent_chapter_id)
            .where(questions.c.visibility == "PUBLISHED", questions.c.archived_at.is_(None))
        )
        return [tuple(r) for r in rows.all()]

    async def draft_shortages(self, since: datetime) -> list[list[dict]]:
        rows = await self._session.execute(select(ExamDraft.shortages).where(ExamDraft.created_at >= since))
        return [r or [] for r in rows.scalars()]

    # ---- vận hành ---------------------------------------------------------------------------------------

    async def pdf_imports(self, since: datetime) -> list[tuple[str, str, datetime]]:
        rows = await self._session.execute(
            select(PdfImport.status, PdfImport.stage, PdfImport.created_at).where(PdfImport.created_at >= since))
        return [tuple(r) for r in rows.all()]

    async def pdf_draft_status(self) -> dict[str, int]:
        rows = await self._session.execute(select(PdfDraft.status, func.count()).group_by(PdfDraft.status))
        return {status: count for status, count in rows.all()}

    async def credit_moves(self, since: datetime) -> list[tuple[datetime, int]]:
        rows = await self._session.execute(
            select(CreditLedger.created_at, CreditLedger.delta).where(CreditLedger.created_at >= since))
        return [tuple(r) for r in rows.all()]

    async def chat_sessions(self, since: datetime) -> list[tuple[int, datetime]]:
        rows = await self._session.execute(
            select(ExamChatSession.session_id, ExamChatSession.created_at)
            .where(ExamChatSession.created_at >= since, ExamChatSession.user_id.is_not(None)))
        return [tuple(r) for r in rows.all()]

    async def drafts_by_session(self, session_ids: list[int]) -> list[tuple[int, int]]:
        if not session_ids:
            return []
        rows = await self._session.execute(
            select(ExamDraft.session_id, ExamDraft.draft_id).where(ExamDraft.session_id.in_(session_ids)))
        return [tuple(r) for r in rows.all()]

    async def attempted_draft_ids(self, draft_ids: list[int]) -> set[int]:
        if not draft_ids:
            return set()
        rows = await self._session.execute(
            select(ExamAttempt.draft_id).where(ExamAttempt.draft_id.in_(draft_ids)).distinct())
        return set(rows.scalars())
