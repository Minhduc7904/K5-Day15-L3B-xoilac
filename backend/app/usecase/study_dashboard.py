from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from app.models.exam_attempt import ExamAttempt
from app.repositories.exam_attempts import ExamAttemptRepository
from app.repositories.question_bank_repository import QuestionBankRepository
from app.repositories.student_profiles import StudentProfileRepository
from app.service.exam_chat_sources import HISTORY_ATTEMPTS, HISTORY_DAYS, StudentHistory
from app.usecase import study_stats
from app.usecase.study_stats import GradedAttempt

MAX_ATTEMPTS = 500  # chặn chi phí nạp; đủ cho streak 84 ngày và thống kê chương của học sinh bình thường


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def to_graded(row: ExamAttempt) -> GradedAttempt:
    """Đổi một lượt đã chấm sang dạng thuần cho `study_stats`. Tiêu đề lấy từ bản đề lúc bắt đầu."""
    result = row.result or {}
    finished = _utc(row.finished_at or row.graded_at or row.started_at)
    statuses = {}
    conflicts = set()
    for entry in result.get("results", []):
        code, status = entry.get("code"), entry.get("status")
        if not code:
            continue
        if code in statuses and statuses[code] != status:
            conflicts.add(code)
        statuses[code] = status
    return GradedAttempt(
        attempt_id=row.attempt_id, draft_id=row.draft_id, title=row.snapshot.get("title") or "Đề luyện tập",
        started_at=_utc(row.started_at), finished_at=finished,
        duration_minutes=(row.snapshot.get("structure") or {}).get("duration_minutes") or 0,
        score=result.get("score") or 0.0, reason=row.reason, items=row.snapshot.get("items", []),
        statuses=statuses, conflicts=conflicts, graded_at=_utc(row.graded_at) if row.graded_at else finished,
        answers=row.progress.get("answers", {}), time_ms=row.progress.get("time_ms", {}),
    )


class StudyDashboard:
    def __init__(self, attempts: ExamAttemptRepository, bank: QuestionBankRepository):
        self.attempts, self.bank = attempts, bank

    async def graded(
        self, user_id: int, limit: int = MAX_ATTEMPTS, *, by_grading_time: bool = False,
    ) -> list[GradedAttempt]:
        return [to_graded(row) for row in await self.attempts.graded(user_id, limit, by_grading_time=by_grading_time)]

    async def get(self, user_id: int) -> dict:
        graded = await self.graded(user_id)
        catalog = await self.bank.chapter_catalog() if graded else {}
        return study_stats.dashboard(graded, catalog, study_stats.study_date(datetime.now(UTC)))


class AttemptHistory:
    """Lịch sử làm bài thật cho agent "ôn chương yếu": đúng/tổng theo chương cha từ các lượt đã chấm."""

    def __init__(self, dashboard: StudyDashboard):
        self.dashboard = dashboard

    async def get(
        self, student_ref: str, *, grade: int | None = None, chapter_codes: Sequence[str] = (),
    ) -> StudentHistory | None:
        if not (student_ref.startswith("U") and student_ref[1:].isdigit()):
            return None
        user_id = int(student_ref[1:])
        graded = await self.dashboard.graded(user_id, HISTORY_ATTEMPTS, by_grading_time=True)
        if not graded:
            return None
        if grade is None and not chapter_codes:
            profile = await StudentProfileRepository(self.dashboard.attempts.session).get(user_id)
            grade = profile.grade if profile else None
        catalog = await self.dashboard.bank.chapter_catalog()
        cutoff = await self.dashboard.attempts.clock() - timedelta(days=HISTORY_DAYS)
        recent = [attempt for attempt in graded if (attempt.graded_at or attempt.finished_at) >= cutoff]
        history = study_stats.attempt_review(recent, catalog, grade, chapter_codes)
        history.latest_at = graded[0].finished_at
        return history
