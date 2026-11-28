from datetime import datetime

from pydantic import BaseModel


class StreakDay(BaseModel):
    date: str
    studied: bool


class StreakOut(BaseModel):
    current: int
    best: int
    days: list[StreakDay]


class TotalsOut(BaseModel):
    exams: int
    questions: int
    minutes: int
    average: float | None


class ScorePoint(BaseModel):
    attempt_id: int
    draft_id: int
    title: str
    date: datetime
    score: float


class ChapterStatOut(BaseModel):
    code: str
    name: str
    grade: int | None
    correct: int
    total: int


class RecentAttempt(BaseModel):
    attempt_id: int
    started_at: datetime
    finished_at: datetime
    duration_seconds: int
    score: float
    correct: int
    total: int
    answered: int
    reason: str | None


class RecentExam(BaseModel):
    draft_id: int
    title: str
    duration_minutes: int
    question_count: int


class RecentItem(BaseModel):
    attempt: RecentAttempt
    exam: RecentExam


class DashboardOut(BaseModel):
    streak: StreakOut
    totals: TotalsOut
    scores: list[ScorePoint]
    chapters: list[ChapterStatOut]
    recent: list[RecentItem]
