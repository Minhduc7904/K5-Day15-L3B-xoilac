"""Thống kê học tập của một học sinh, tính từ các lượt làm bài đã chấm.

Toàn bộ là hàm thuần trên dữ liệu đã nạp, để dashboard và nguồn lịch sử của agent dùng chung một cách đếm
và để kiểm thử không cần cơ sở dữ liệu.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from app.core.study_time import STUDY_TZ, study_date
from app.repositories.question_bank_repository import grade_of

DAYS = 84
RECENT = 5


@dataclass(frozen=True)
class GradedAttempt:
    attempt_id: int
    draft_id: int
    title: str
    started_at: datetime
    finished_at: datetime
    duration_minutes: int
    score: float
    reason: str | None
    items: list[dict] = field(default_factory=list)
    statuses: dict[str, str] = field(default_factory=dict)
    answers: dict[str, dict] = field(default_factory=dict)
    time_ms: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def correct(self) -> int:
        return sum(status == "correct" for status in self.statuses.values())

    @property
    def answered(self) -> int:
        return sum(has_answer(entry.get("value")) for entry in self.answers.values())

    @property
    def duration_seconds(self) -> int:
        """Thời gian làm thực tế: tổng thời gian từng câu, thiếu thì lấy khoảng nộp trừ bắt đầu và không vượt thời lượng đề."""
        active = sum(self.time_ms.values()) // 1000
        wall = int((self.finished_at - self.started_at).total_seconds())
        seconds = active or wall
        if self.duration_minutes > 0:
            seconds = min(seconds, self.duration_minutes * 60)
        return max(1, seconds)


def has_answer(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return any(part is not None for part in value)


def chapter_root(item: dict, catalog: dict[str, dict]) -> str | None:
    """Mã chương cha của câu (đề theo mẫu có thể ghép nhiều mã vào `chapter`, nên ưu tiên `chapter_codes`)."""
    codes = item.get("chapter_codes") or []
    code = codes[0] if codes else (item.get("chapter") or "").split(",")[0].strip()
    if not code:
        return None
    return (catalog.get(code) or {}).get("parent_code") or code


def chapter_totals(attempts: list[GradedAttempt], catalog: dict[str, dict]) -> dict[str, list[int]]:
    """Mã chương cha → [số câu đúng, số câu]. Câu Đúng/Sai chỉ đúng một phần không tính là đúng."""
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for attempt in attempts:
        for item in attempt.items:
            root = chapter_root(item, catalog)
            if root is None:
                continue
            entry = totals[root]
            entry[1] += 1
            entry[0] += attempt.statuses.get(item["code"]) == "correct"
    return dict(totals)


def streak(attempts: list[GradedAttempt], today: date) -> dict:
    studied = {study_date(attempt.finished_at) for attempt in attempts}
    cursor = today if today in studied else today - timedelta(days=1)
    current = 0
    while cursor in studied:
        current += 1
        cursor -= timedelta(days=1)
    best = run = 0
    previous: date | None = None
    for day in sorted(studied):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    days = []
    for offset in range(DAYS - 1, -1, -1):
        day = today - timedelta(days=offset)
        days.append({"date": datetime.combine(day, time.min, STUDY_TZ).isoformat(), "studied": day in studied})
    return {"current": current, "best": best, "days": days}


def dashboard(attempts: list[GradedAttempt], catalog: dict[str, dict], today: date) -> dict:
    """`attempts` là các lượt đã chấm của một học sinh. Trả dữ liệu theo hợp đồng `DashboardOut`."""
    ordered = sorted(attempts, key=lambda a: (a.finished_at, a.attempt_id))
    stats = chapter_totals(ordered, catalog)
    chapters = [
        {"code": code, "name": (catalog.get(code) or {}).get("name") or code, "grade": grade_of(code),
         "correct": correct, "total": total}
        for code, (correct, total) in stats.items()
    ]
    chapters.sort(key=lambda c: (c["correct"] / c["total"], c["code"]))
    return {
        "streak": streak(ordered, today),
        "totals": {
            "exams": len({a.draft_id for a in ordered}),
            "questions": sum(a.total for a in ordered),
            "minutes": round(sum(a.duration_seconds for a in ordered) / 60),
            "average": sum(a.score for a in ordered) / len(ordered) if ordered else None,
        },
        "scores": [{"attempt_id": a.attempt_id, "draft_id": a.draft_id, "title": a.title,
                    "date": a.finished_at, "score": a.score} for a in ordered],
        "chapters": chapters,
        "recent": [
            {
                "attempt": {"attempt_id": a.attempt_id, "started_at": a.started_at, "finished_at": a.finished_at,
                            "duration_seconds": a.duration_seconds, "score": a.score, "correct": a.correct,
                            "total": a.total, "answered": a.answered, "reason": a.reason},
                "exam": {"draft_id": a.draft_id, "title": a.title, "duration_minutes": a.duration_minutes,
                         "question_count": a.total},
            }
            for a in reversed(ordered[-RECENT:])
        ],
    }
