"""API mẫu cấu trúc đề (issue #5).

Quyền (Auth #8):
- Tạo, sửa, duyệt, xem danh sách và chi tiết mọi trạng thái: chỉ admin (AdminDep).
- /lookup: mọi tài khoản đã đăng nhập (CurrentUserDep). Đây là hợp đồng đọc cho pipeline học sinh (#4), chỉ trả mẫu
  đã duyệt nên không lộ mẫu nháp cho học sinh.
"""
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AdminDep, CurrentUserDep, ExamTemplateUseCaseDep
from app.schemas.auth import ErrorOut
from app.schemas.exam_template import ExamTemplateIn, ExamTemplateOut, ExamType, TemplateStatus
from app.usecase.exam_template_rules import TemplateValidationError

router = APIRouter(
    prefix="/exam-templates",
    tags=["exam-templates"],
    responses={
        401: {"model": ErrorOut, "description": "Chưa đăng nhập hoặc phiên không còn hiệu lực"},
        403: {"model": ErrorOut, "description": "FORBIDDEN_ROLE (route quản trị) / ACCOUNT_DISABLED"},
    },
)

NOT_FOUND = "Không có mẫu cấu trúc đề này"


def _invalid(e: TemplateValidationError) -> HTTPException:
    # 422 viết số để không phụ thuộc tên hằng (Starlette mới đổi tên HTTP_422_UNPROCESSABLE_ENTITY).
    return HTTPException(422, {"message": "Mẫu không hợp lệ", "errors": e.errors})


# /lookup phải khai báo trước /{template_id} để không bị bắt nhầm thành id.
@router.get("/lookup", response_model=list[ExamTemplateOut])
async def lookup_templates(
    _: CurrentUserDep,
    usecase: ExamTemplateUseCaseDep,
    exam_type: ExamType,
    grade: int | None = Query(default=None, ge=10, le=12),
    version_label: str | None = Query(default=None, max_length=50),
):
    return await usecase.lookup(exam_type=exam_type, grade=grade, version_label=version_label)


@router.post("", response_model=ExamTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(_: AdminDep, body: ExamTemplateIn, usecase: ExamTemplateUseCaseDep):
    try:
        return await usecase.create(body)
    except TemplateValidationError as e:
        raise _invalid(e) from e


@router.get("", response_model=list[ExamTemplateOut])
async def list_templates(
    _: AdminDep,
    usecase: ExamTemplateUseCaseDep,
    status_filter: TemplateStatus | None = Query(default=None, alias="status"),
    exam_type: ExamType | None = None,
    grade: int | None = Query(default=None, ge=10, le=12),
):
    return await usecase.list(status=status_filter, exam_type=exam_type, grade=grade)


@router.get("/{template_id}", response_model=ExamTemplateOut)
async def get_template(_: AdminDep, template_id: int, usecase: ExamTemplateUseCaseDep):
    item = await usecase.get(template_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return item


@router.put("/{template_id}", response_model=ExamTemplateOut)
async def update_template(_: AdminDep, template_id: int, body: ExamTemplateIn, usecase: ExamTemplateUseCaseDep):
    try:
        item = await usecase.update(template_id, body)
    except TemplateValidationError as e:
        raise _invalid(e) from e
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return item


@router.post("/{template_id}/approve", response_model=ExamTemplateOut)
async def approve_template(_: AdminDep, template_id: int, usecase: ExamTemplateUseCaseDep):
    try:
        item = await usecase.approve(template_id)
    except TemplateValidationError as e:
        raise _invalid(e) from e
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return item
