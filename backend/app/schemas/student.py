from datetime import date, datetime, time
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

ExamPeriod = Literal["midterm_1", "final_1", "midterm_2", "final_2", "national_high_school"]
Weekday = Literal[1, 2, 3, 4, 5, 6]
SchoolName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    school_name: SchoolName
    grade: Literal[10, 11, 12]
    target_score: Literal[7, 8, 9]
    exam_period: ExamPeriod
    study_days: list[Weekday] = Field(min_length=1, max_length=6)
    reminder_time: time | None = None
    display_name: DisplayName | None = None

    @field_validator("study_days")
    @classmethod
    def unique_days(cls, days: list[int]) -> list[int]:
        if len(set(days)) != len(days):
            raise ValueError("Chọn mỗi ngày một lần")
        return sorted(days)

    @field_validator("reminder_time")
    @classmethod
    def local_minutes(cls, value: time | None) -> time | None:
        if value is not None and (value.tzinfo is not None or value.second or value.microsecond):
            raise ValueError("Dùng giờ địa phương theo định dạng HH:MM")
        return value


class ProfileOut(BaseModel):
    school_name: str
    grade: int
    target_score: int
    exam_period: ExamPeriod
    study_days: list[int]
    reminder_time: time | None
    display_name: str | None
    email: str
    email_verified: bool
    joined_at: datetime


class ProfileStatusOut(BaseModel):
    completed: bool
    profile: ProfileOut | None
    email_verified: bool


class CreditEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    delta: int
    balance_after: int
    reason: str
    effective_on: date
    created_at: datetime


class CreditsOut(BaseModel):
    balance: int
    limit: int
    daily_grant: int
    history: list[CreditEntryOut]
    next_before_id: int | None
