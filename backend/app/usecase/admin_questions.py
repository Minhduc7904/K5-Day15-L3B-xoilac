"""Admin quản lý ngân hàng câu hỏi (#11). Không biết HTTP.

- Kiểm dữ liệu theo loại câu (`validate_question`, hàm thuần, có test riêng).
- Tạo/sửa câu + lựa chọn/mệnh đề + chương trong một giao dịch, làm mới searchable_content.
- Lưu trữ/khôi phục là mềm (archived_at); không xoá cứng, đề và lịch sử cũ vẫn đọc được.
"""
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.repositories.admin_question_repository import AdminQuestionRepository
from app.repositories.question_bank_repository import grade_of, question_code
from app.schemas.admin_bank import QuestionIn
from app.usecase.auth import AuthError

MEDIA_REF = re.compile(r"media:(\d+)")
IMAGE_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
CHOICE_TYPES = {"SINGLE_CHOICE", "MULTIPLE_CHOICE"}


class QuestionNotFound(AuthError):
    code = "QUESTION_NOT_FOUND"
    message = "Không có câu hỏi này"


class InvalidQuestion(AuthError):
    code = "INVALID_QUESTION"
    message = "Câu hỏi chưa hợp lệ"


class MediaNotFound(AuthError):
    code = "MEDIA_NOT_FOUND"
    message = "Không tìm thấy ảnh"


class InvalidMedia(AuthError):
    code = "INVALID_MEDIA"
    message = "Ảnh không hợp lệ (PNG, JPEG, WEBP hoặc GIF, tối đa 5 MiB)"


def validate_question(body: QuestionIn) -> str | None:
    """Hàm thuần: trả thông báo lỗi tiếng Việt, hoặc None nếu hợp lệ. Backend và form admin dùng cùng luật."""
    options = body.statements
    correct = sum(1 for s in options if s.is_correct)
    if body.type in CHOICE_TYPES and len(options) < 2:
        return "Câu trắc nghiệm cần ít nhất 2 lựa chọn"
    if body.type == "SINGLE_CHOICE" and correct != 1:
        return "Câu một đáp án cần đúng 1 lựa chọn đúng"
    if body.type == "MULTIPLE_CHOICE" and correct < 1:
        return "Câu nhiều đáp án cần ít nhất 1 lựa chọn đúng"
    if body.type == "TRUE_FALSE" and not options:
        return "Câu đúng/sai cần ít nhất 1 mệnh đề"
    if body.type == "SHORT_ANSWER" and not (body.correct_answer and body.correct_answer.strip()):
        return "Câu trả lời ngắn cần đáp án"
    if body.type in {"SHORT_ANSWER", "ESSAY"} and options:
        return "Câu trả lời ngắn và tự luận không có lựa chọn"
    if len(set(body.chapter_ids)) != len(body.chapter_ids):
        return "Chương bị lặp"
    return None


def derived_answer(body: QuestionIn) -> str | None:
    """Đáp án dạng chữ khi admin để trống: trắc nghiệm → chữ cái (vd "AC"), đúng/sai → chuỗi Đ/S."""
    if body.correct_answer:
        return body.correct_answer
    if body.type in CHOICE_TYPES:
        return "".join(chr(65 + i) for i, s in enumerate(body.statements) if s.is_correct) or None
    if body.type == "TRUE_FALSE":
        return "".join("Đ" if s.is_correct else "S" for s in body.statements)
    return None


def searchable_text(body: QuestionIn) -> str:
    """Văn bản tìm kiếm: nội dung + lựa chọn, bỏ tham chiếu ảnh và ký hiệu $, gộp khoảng trắng, chữ thường."""
    parts = [body.content, *(s.content for s in body.statements)]
    text = " ".join(parts)
    text = re.sub(r"!\[[^\]]*\]\(media:\d+\)", " ", text).replace("$", " ")
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip().lower()


def media_ids(body: QuestionIn) -> list[int]:
    values = [body.content, body.solution or "", *(s.content for s in body.statements)]
    return sorted({int(m) for v in values for m in MEDIA_REF.findall(v)})


def status_of(row: dict) -> str:
    return "ARCHIVED" if row.get("archived_at") else row["visibility"]


def _summary(row: dict) -> dict:
    return {**row, "code": question_code(row["question_id"]), "status": status_of(row)}


@dataclass
class QuestionPage:
    items: list[dict]
    total: int
    page: int
    page_size: int


_CODE = re.compile(r"^\s*Q0*(\d{1,9})\s*$", re.IGNORECASE)


class AdminQuestionUseCase:
    def __init__(self, repo: AdminQuestionRepository, storage, bucket: str) -> None:
        self._repo = repo
        self._storage = storage
        self._bucket = bucket

    async def list_questions(self, *, q: str | None, grade: int | None, chapter_id: int | None, qtype: str | None,
                   difficulty: str | None, status: str | None, page: int, page_size: int) -> QuestionPage:
        q = q.strip() if q else None
        code = _CODE.match(q) if q else None
        question_id = int(code.group(1)) if code else (int(q) if q and q.isdigit() else None)
        items, total = await self._repo.search(
            q=q.lower() if q else None, question_id=question_id, grade=grade, chapter_id=chapter_id,
            qtype=qtype, difficulty=difficulty, status=status, page=page, page_size=page_size)
        return QuestionPage([_summary(r) for r in items], total, page, page_size)

    async def get(self, question_id: int) -> dict:
        row = await self._repo.get(question_id)
        if row is None:
            raise QuestionNotFound()
        texts = [row["content"], row["solution"] or "", *(s["content"] for s in row["statements"])]
        row["media_ids"] = sorted({int(m) for t in texts for m in MEDIA_REF.findall(t)})
        return _summary(row)

    async def _prepare(self, body: QuestionIn, question_id: int | None) -> tuple[dict, list[dict]]:
        problem = validate_question(body)
        if problem:
            raise InvalidQuestion(problem)
        found = await self._repo.chapters_by_ids(body.chapter_ids)
        missing = set(body.chapter_ids) - {c["chapter_id"] for c in found}
        if missing:
            raise InvalidQuestion(f"Không có chương: {', '.join(map(str, sorted(missing)))}")
        roots = await self._repo.root_codes(body.chapter_ids)
        grades = {grade_of(code) for code in roots.values() if code and grade_of(code)}
        if len(grades) > 1:
            raise InvalidQuestion("Các chương phải cùng một khối lớp")
        grade = body.grade or (grades.pop() if grades else None)
        if body.grade and grades and body.grade not in grades:
            raise InvalidQuestion(f"Khối {body.grade} không khớp với khối của chương đã chọn")
        refs = media_ids(body)
        if refs:
            missing_media = set(refs) - await self._repo.ready_images(refs)
            if missing_media:
                raise InvalidQuestion(f"Ảnh không tồn tại: {', '.join(f'media:{i}' for i in sorted(missing_media))}")
        if question_id is not None:
            owned = await self._repo.existing_statement_ids(question_id)
            foreign = {s.statement_id for s in body.statements if s.statement_id} - owned
            if foreign:
                raise InvalidQuestion("Lựa chọn không thuộc câu hỏi này")
        fields = {
            "content": body.content, "type": body.type, "difficulty": body.difficulty, "grade": grade,
            "visibility": body.visibility, "correct_answer": derived_answer(body), "solution": body.solution or None,
            "searchable_content": searchable_text(body), "subject_id": found[0]["subject_id"],
        }
        options = [{"statement_id": s.statement_id, "content": s.content, "is_correct": s.is_correct, "order": i}
                   for i, s in enumerate(body.statements, 1)]
        return fields, options

    async def create(self, body: QuestionIn) -> dict:
        fields, options = await self._prepare(body, None)
        try:
            question_id = await self._repo.insert_question({**fields, "slug": f"admin-{uuid4().hex}"})
            await self._repo.replace_statements(question_id, options)
            await self._repo.replace_chapters(question_id, body.chapter_ids)
            await self._repo.commit()
        except Exception:
            await self._repo.rollback()
            raise
        return await self.get(question_id)

    async def update(self, question_id: int, body: QuestionIn) -> dict:
        if await self._repo.get(question_id) is None:
            raise QuestionNotFound()
        fields, options = await self._prepare(body, question_id)
        try:
            await self._repo.update_question(question_id, {**fields, "updated_at": datetime.now(UTC)})
            await self._repo.replace_statements(question_id, options)
            await self._repo.replace_chapters(question_id, body.chapter_ids)
            await self._repo.commit()
        except Exception:
            await self._repo.rollback()
            raise
        return await self.get(question_id)

    async def archive(self, question_id: int) -> dict:
        row = await self._repo.get(question_id)
        if row is None:
            raise QuestionNotFound()
        if row["archived_at"] is None:  # lưu trữ lại câu đã lưu trữ: giữ mốc thời gian cũ
            await self._repo.set_archived(question_id, datetime.now(UTC))
            await self._repo.commit()
        return await self.get(question_id)

    async def restore(self, question_id: int) -> dict:
        if await self._repo.get(question_id) is None:
            raise QuestionNotFound()
        await self._repo.set_archived(question_id, None)
        await self._repo.commit()
        return await self.get(question_id)

    async def upload_image(self, filename: str, mime: str, data: bytes) -> int:
        extension = IMAGE_TYPES.get(mime)
        if extension is None or not data or len(data) > MAX_IMAGE_BYTES:
            raise InvalidMedia()
        name = f"{uuid4().hex}.{extension}"
        key = f"question-media/{name}"
        await self._storage.put(key, data, mime)
        media_id = await self._repo.add_image(
            file_name=name, original_name=(filename or name)[:255], mime_type=mime, file_size=len(data),
            type="IMAGE", status="READY", bucket_name=self._bucket, object_key=key)
        await self._repo.commit()
        return media_id

    async def image(self, media_id: int) -> tuple[bytes, str]:
        row = await self._repo.image(media_id)
        stored = await self._storage.get(row["object_key"]) if row else None
        if stored is None:
            raise MediaNotFound()
        return stored[0], row["mime_type"]
