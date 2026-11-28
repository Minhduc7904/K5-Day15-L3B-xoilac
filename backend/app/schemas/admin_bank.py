"""Schema API admin quản lý ngân hàng câu hỏi và danh mục chương (#11)."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

QuestionType = Literal["SINGLE_CHOICE", "MULTIPLE_CHOICE", "TRUE_FALSE", "SHORT_ANSWER", "ESSAY"]
Difficulty = Literal["NB", "TH", "VD", "VDC"]
Visibility = Literal["DRAFT", "PRIVATE", "PUBLISHED"]
# Trạng thái hiển thị: ARCHIVED khi archived_at khác NULL, ngược lại là visibility.
QuestionStatus = Literal["DRAFT", "PRIVATE", "PUBLISHED", "ARCHIVED"]
Grade = Annotated[int, Field(ge=10, le=12)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]


class ChapterRef(BaseModel):
    chapter_id: int
    code: str | None
    name: str


class StatementIn(BaseModel):
    statement_id: int | None = Field(None, description="Giữ id để sửa tại chỗ; bỏ trống là lựa chọn mới")
    content: Text
    is_correct: bool = False


class StatementOut(BaseModel):
    statement_id: int
    content: str
    is_correct: bool
    order: int | None


class QuestionIn(BaseModel):
    content: Text
    type: QuestionType
    difficulty: Difficulty | None = None
    grade: Grade | None = Field(None, description="Bỏ trống thì suy từ mã chương")
    visibility: Visibility = "PUBLISHED"
    correct_answer: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
    solution: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20000)] | None = None
    statements: list[StatementIn] = Field(default_factory=list, max_length=12)
    chapter_ids: list[int] = Field(min_length=1, max_length=10)


class QuestionSummary(BaseModel):
    question_id: int
    code: str
    content: str
    type: str
    difficulty: str | None
    grade: int | None
    visibility: str
    status: QuestionStatus
    archived_at: datetime | None
    updated_at: datetime | None
    chapters: list[ChapterRef]


class QuestionDetail(QuestionSummary):
    correct_answer: str | None
    solution: str | None
    statements: list[StatementOut]
    media_ids: list[int]
    exam_count: int = Field(description="Số đề (questions_exams) đang tham chiếu câu này")
    created_at: datetime | None


class QuestionListOut(BaseModel):
    items: list[QuestionSummary]
    total: int
    page: int
    page_size: int


class MediaOut(BaseModel):
    media_id: int
    url: str = Field(description="Đường dẫn tương đối để admin xem ảnh")


class ChapterIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=191)]
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=191)]
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=191)] | None = None
    parent_chapter_id: int | None = None
    order_in_parent: Annotated[int, Field(ge=0, le=10000)] | None = None


class ChapterNode(BaseModel):
    chapter_id: int
    code: str | None
    name: str
    slug: str | None
    parent_chapter_id: int | None
    order_in_parent: int | None
    level: int
    grade: int | None
    question_count: int = Field(description="Số câu gắn trực tiếp vào chương")
    subtree_question_count: int = Field(description="Số câu phân biệt gắn vào chương hoặc chương con")
    children: list["ChapterNode"] = Field(default_factory=list)
