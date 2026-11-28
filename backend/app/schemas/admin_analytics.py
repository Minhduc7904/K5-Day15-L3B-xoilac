"""Schema các API thống kê phân tích cho dashboard admin. Chỉ chứa số tổng hợp, không có dữ liệu cá nhân."""
from datetime import datetime

from pydantic import BaseModel, field_serializer


class Kpi(BaseModel):
    key: str
    value: float | None
    previous: float | None = None
    series: list[float] = []


class Attention(BaseModel):
    pending_pdf_drafts: int
    draft_questions: int
    failed_imports: int


class OverviewOut(BaseModel):
    range_days: int
    generated_at: datetime
    kpis: list[Kpi]
    attention: Attention

    @field_serializer("generated_at")
    def _iso_utc(self, value: datetime) -> str:
        return value.isoformat().replace("+00:00", "Z")


class Count(BaseModel):
    key: str
    count: int


class FunnelStep(BaseModel):
    key: str
    label: str
    count: int


class GrowthOut(BaseModel):
    range_days: int
    days: list[str]
    signups: list[int]
    dau: list[int]
    wau: list[int]
    active_students: int
    stickiness: float | None
    funnel: list[FunnelStep]
    heatmap: list[list[int]]
    grades: list[Count]
    targets: list[Count]


class ScoreBin(BaseModel):
    label: str
    count: int


class WeekScore(BaseModel):
    week: str
    attempts: int
    average: float | None


class WeekOutcome(BaseModel):
    week: str
    manual: int
    timeout: int
    in_progress: int


class ChapterRate(BaseModel):
    code: str
    name: str
    correct: int
    total: int
    rate: float


class LearningOut(BaseModel):
    range_days: int
    graded: int
    median: float | None
    average: float | None
    bins: list[ScoreBin]
    weekly: list[WeekScore]
    outcomes: list[WeekOutcome]
    chapters: list[ChapterRate]
    chapters_hidden: int
    min_answers: int


class CoverageRow(BaseModel):
    code: str
    name: str
    grade: int | None
    counts: dict[str, int]
    total: int


class ShortageChapter(BaseModel):
    code: str
    name: str
    missing: int
    occurrences: int


class Shortages(BaseModel):
    drafts: int
    drafts_with_shortage: int
    chapters: list[ShortageChapter]


class BankOut(BaseModel):
    range_days: int
    published: int
    draft: int
    private: int
    archived: int
    by_type: list[Count]
    by_grade: list[Count]
    by_difficulty: list[Count]
    coverage: list[CoverageRow]
    shortages: Shortages


class ImportStats(BaseModel):
    total: int
    success_rate: float | None
    by_status: list[Count]
    failed_by_stage: list[Count]
    completed: list[int]
    failed: list[int]
    in_flight: list[int]


class CreditStats(BaseModel):
    granted: list[int]
    spent: list[int]


class ChatStats(BaseModel):
    sessions: int
    with_draft: int
    with_attempt: int
    daily: list[int]


class OperationsOut(BaseModel):
    range_days: int
    days: list[str]
    imports: ImportStats
    pdf_drafts: dict[str, int]
    credits: CreditStats
    chat: ChatStats
