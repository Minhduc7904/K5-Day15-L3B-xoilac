"""Admin quản lý danh mục chương (#11). Mọi route cần AdminDep (khách 401, học sinh 403 FORBIDDEN_ROLE)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import AdminChapterUseCaseDep, AdminDep, require_role
from app.api.errors import to_api_error
from app.schemas.admin_bank import ChapterIn, ChapterNode
from app.schemas.auth import ErrorOut
from app.usecase.auth import AuthError

router = APIRouter(
    prefix="/admin/chapters",
    tags=["admin-question-bank"],
    dependencies=[Depends(require_role("admin"))],
    responses={
        401: {"model": ErrorOut, "description": "SESSION_*: chưa đăng nhập hoặc phiên hết hạn"},
        403: {"model": ErrorOut, "description": "FORBIDDEN_ROLE: không phải admin"},
    },
)

_WRITE = {
    404: {"model": ErrorOut, "description": "CHAPTER_NOT_FOUND (chương hoặc chương cha)"},
    409: {"model": ErrorOut, "description": "CHAPTER_CODE_TAKEN / CHAPTER_IN_USE"},
    422: {"model": ErrorOut, "description": "CHAPTER_CYCLE / INVALID_CHAPTER hoặc lỗi schema"},
}


@router.get("", response_model=list[ChapterNode])
async def chapter_tree(_: AdminDep, usecase: AdminChapterUseCaseDep,
                       grade: Annotated[int | None, Query(ge=10, le=12)] = None):
    """Cây chương theo parent_chapter_id, sắp theo order_in_parent, kèm số câu."""
    return await usecase.tree(grade)


@router.post("", response_model=ChapterNode, status_code=status.HTTP_201_CREATED, responses=_WRITE)
async def create_chapter(body: ChapterIn, _: AdminDep, usecase: AdminChapterUseCaseDep):
    try:
        return await usecase.create(body)
    except AuthError as e:
        raise to_api_error(e) from None


@router.put("/{chapter_id}", response_model=ChapterNode, responses=_WRITE)
async def update_chapter(chapter_id: int, body: ChapterIn, _: AdminDep, usecase: AdminChapterUseCaseDep):
    """Đổi tên, mã, slug, chương cha, thứ tự. level của cả nhánh được tính lại."""
    try:
        return await usecase.update(chapter_id, body)
    except AuthError as e:
        raise to_api_error(e) from None


@router.delete("/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_WRITE)
async def delete_chapter(chapter_id: int, _: AdminDep, usecase: AdminChapterUseCaseDep) -> Response:
    """Chỉ xoá được chương không còn chương con và không còn câu nào gắn vào."""
    try:
        await usecase.delete(chapter_id)
    except AuthError as e:
        raise to_api_error(e) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
