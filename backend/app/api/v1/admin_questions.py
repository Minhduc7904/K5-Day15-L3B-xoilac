"""Admin quản lý ngân hàng câu hỏi (#11). Mọi route cần AdminDep (khách 401, học sinh 403 FORBIDDEN_ROLE).

Route chỉ xử lý HTTP; luật kiểm câu theo loại và lưu trữ mềm nằm ở usecase.admin_questions.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, UploadFile, status

from app.api.deps import AdminDep, AdminQuestionUseCaseDep, require_role
from app.api.errors import to_api_error
from app.schemas.admin_bank import (
    Difficulty, MediaOut, QuestionDetail, QuestionIn, QuestionListOut, QuestionStatus, QuestionType,
)
from app.schemas.auth import ErrorOut
from app.usecase.auth import AuthError

router = APIRouter(
    prefix="/admin/questions",
    tags=["admin-question-bank"],
    dependencies=[Depends(require_role("admin"))],
    responses={
        401: {"model": ErrorOut, "description": "SESSION_*: chưa đăng nhập hoặc phiên hết hạn"},
        403: {"model": ErrorOut, "description": "FORBIDDEN_ROLE: không phải admin"},
    },
)

_NOT_FOUND = {404: {"model": ErrorOut, "description": "QUESTION_NOT_FOUND"}}
_INVALID = {422: {"model": ErrorOut, "description": "INVALID_QUESTION hoặc lỗi schema"}}


@router.get("", response_model=QuestionListOut)
async def list_questions(
    _: AdminDep,
    usecase: AdminQuestionUseCaseDep,
    q: Annotated[str | None, Query(max_length=200, description="Tìm trong nội dung (ILIKE) hoặc mã câu Q00012")] = None,
    grade: Annotated[int | None, Query(ge=10, le=12)] = None,
    chapter_id: Annotated[int | None, Query(description="Gồm cả chương con cháu")] = None,
    type_: Annotated[QuestionType | None, Query(alias="type")] = None,
    difficulty: Difficulty | None = None,
    status_: Annotated[QuestionStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    result = await usecase.list_questions(q=q, grade=grade, chapter_id=chapter_id, qtype=type_, difficulty=difficulty,
                                status=status_, page=page, page_size=page_size)
    return QuestionListOut(items=result.items, total=result.total, page=result.page, page_size=result.page_size)


@router.post("/media", response_model=MediaOut, status_code=status.HTTP_201_CREATED,
             responses={422: {"model": ErrorOut, "description": "INVALID_MEDIA"}})
async def upload_media(file: UploadFile, _: AdminDep, usecase: AdminQuestionUseCaseDep):
    """Tải một ảnh lên MinIO; chèn vào nội dung bằng `![mô tả](media:ID)`."""
    try:
        media_id = await usecase.upload_image(file.filename or "", file.content_type or "", await file.read())
    except AuthError as e:
        raise to_api_error(e) from None
    return MediaOut(media_id=media_id, url=f"/api/v1/admin/questions/media/{media_id}")


@router.get("/media/{media_id}", response_class=Response,
            responses={404: {"model": ErrorOut, "description": "MEDIA_NOT_FOUND"}})
async def get_media(media_id: int, _: AdminDep, usecase: AdminQuestionUseCaseDep):
    try:
        data, mime = await usecase.image(media_id)
    except AuthError as e:
        raise to_api_error(e) from None
    return Response(data, media_type=mime, headers={"Cache-Control": "private, max-age=300",
                                                   "X-Content-Type-Options": "nosniff"})


@router.get("/{question_id}", response_model=QuestionDetail, responses=_NOT_FOUND)
async def get_question(question_id: int, _: AdminDep, usecase: AdminQuestionUseCaseDep):
    try:
        return await usecase.get(question_id)
    except AuthError as e:
        raise to_api_error(e) from None


@router.post("", response_model=QuestionDetail, status_code=status.HTTP_201_CREATED, responses=_INVALID)
async def create_question(body: QuestionIn, _: AdminDep, usecase: AdminQuestionUseCaseDep):
    try:
        return await usecase.create(body)
    except AuthError as e:
        raise to_api_error(e) from None


@router.put("/{question_id}", response_model=QuestionDetail, responses={**_NOT_FOUND, **_INVALID})
async def update_question(question_id: int, body: QuestionIn, _: AdminDep, usecase: AdminQuestionUseCaseDep):
    try:
        return await usecase.update(question_id, body)
    except AuthError as e:
        raise to_api_error(e) from None


@router.post("/{question_id}/archive", response_model=QuestionDetail, responses=_NOT_FOUND)
async def archive_question(question_id: int, _: AdminDep, usecase: AdminQuestionUseCaseDep):
    """Ngừng sử dụng: không còn được chọn cho đề mới; đề và lịch sử đã tham chiếu vẫn đọc được."""
    try:
        return await usecase.archive(question_id)
    except AuthError as e:
        raise to_api_error(e) from None


@router.post("/{question_id}/restore", response_model=QuestionDetail, responses=_NOT_FOUND)
async def restore_question(question_id: int, _: AdminDep, usecase: AdminQuestionUseCaseDep):
    try:
        return await usecase.restore(question_id)
    except AuthError as e:
        raise to_api_error(e) from None
