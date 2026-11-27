from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

QuestionType = Literal["SINGLE_CHOICE", "MULTIPLE_CHOICE", "TRUE_FALSE", "SHORT_ANSWER", "ESSAY"]
Difficulty = Literal["NB", "TH", "VD", "VDC"]


class ExtractedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ExtractedQuestion(ExtractedRecord):
    section: str
    number: str
    pages: list[int]
    type: QuestionType
    content: str
    statements: list[str]
    image_dependent: bool


class AnswerEvidence(ExtractedRecord):
    section: str | None
    number: str
    page: int
    source: Literal["key", "solution"]
    excerpt: str
    choices: list[int] | None
    truth_values: list[bool | None] | None
    answer: str | None
    solution: str | None


class Extraction(ExtractedRecord):
    questions: list[ExtractedQuestion]
    answers: list[AnswerEvidence]


class DraftStatement(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    content: str = Field(min_length=1)
    isCorrect: bool | None = None


class DraftEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    content: str | None = Field(default=None, min_length=1)
    statements: list[DraftStatement] | None = None
    correctAnswer: str | None = None
    solution: str | None = None
    chapterCodes: list[str] | None = None
    difficulty: Difficulty | None = None
    imageReviewed: bool | None = None
