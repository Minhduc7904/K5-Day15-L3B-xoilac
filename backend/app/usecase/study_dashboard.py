from datetime import UTC, datetime

from app.models.exam_attempt import ExamAttempt
from app.repositories.exam_attempts import ExamAttemptRepository
from app.repositories.question_bank_repository import QuestionBankRepository
from app.service.exam_chat_sources import ChapterResult, StudentHistory
from app.usecase import study_stats
from app.usecase.study_stats import GradedAttempt

MAX_ATTEMPTS = 500  # chặn chi phí nạp; đủ cho streak 84 ngày và thống kê chương của học sinh bình thường


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def to_graded(row: ExamAttempt) -> GradedAttempt:
    """Đổi một lượt đã chấm sang dạng thuần cho `study_stats`. Tiêu đề lấy từ bản đề lúc bắt đầu."""
    result = row.result or {}
    finished = _utc(row.finished_at or row.graded_at or row.started_at)
    return GradedAttempt(
        attempt_id=row.attempt_id, draft_id=row.draft_id, title=row.snapshot.get("title") or "Đề luyện tập",
        started_at=_utc(row.started_at), finished_at=finished,
        duration_minutes=(row.snapshot.get("structure") or {}).get("duration_minutes") or 0,
        score=result.get("score") or 0.0, reason=row.reason, items=row.snapshot.get("items", []),
        statuses={entry["code"]: entry["status"] for entry in result.get("results", [])},
        answers=row.progress.get("answers", {}), time_ms=row.progress.get("time_ms", {}),
    )


class StudyDashboard:
    def __init__(self, attempts: ExamAttemptRepository, bank: QuestionBankRepository):
        self.attempts, self.bank = attempts, bank

    async def graded(self, user_id: int) -> list[GradedAttempt]:
        return [to_graded(row) for row in await self.attempts.graded(user_id, MAX_ATTEMPTS)]

    async def get(self, user_id: int) -> dict:
        graded = await self.graded(user_id)
        catalog = await self.bank.chapter_catalog() if graded else {}
        return study_stats.dashboard(graded, catalog, study_stats.study_date(datetime.now(UTC)))


class AttemptHistory:
    """Lịch sử làm bài thật cho agent "ôn chương yếu": đúng/tổng theo chương cha từ các lượt đã chấm."""

    def __init__(self, dashboard: StudyDashboard):
        self.dashboard = dashboard

    async def get(self, student_ref: str) -> StudentHistory | None:
        if not (student_ref.startswith("U") and student_ref[1:].isdigit()):
            return None
        graded = await self.dashboard.graded(int(student_ref[1:]))
        if not graded:
            return None
        catalog = await self.dashboard.bank.chapter_catalog()
        totals = study_stats.chapter_totals(graded, catalog)
        return StudentHistory(chapters=[ChapterResult(code, correct, total)
                                        for code, (correct, total) in sorted(totals.items())])
