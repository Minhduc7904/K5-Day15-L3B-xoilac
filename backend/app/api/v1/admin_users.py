"""Admin quản lý tài khoản học sinh và admin (#20). Thay thế /admin/accounts của #8.

Mọi route cần AdminDep (khách 401, học sinh 403 FORBIDDEN_ROLE). Luật "admin nào được làm gì với ai"
nằm ở usecase (can_manage), route chỉ đổi lỗi nghiệp vụ thành HTTP.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import AdminDep, UserManagementUseCaseDep, require_role
from app.api.errors import to_api_error
from app.schemas.auth import ErrorOut
from app.schemas.user_admin import ResetPasswordIn, Role, Status, UserAdminOut, UserCreateIn, UserListOut, UserUpdateIn
from app.usecase.auth import AuthError

router = APIRouter(
    prefix="/admin/users",
    tags=["admin"],
    dependencies=[Depends(require_role("admin"))],
    responses={
        401: {"model": ErrorOut, "description": "SESSION_*: chưa đăng nhập hoặc phiên không còn hiệu lực"},
        403: {"model": ErrorOut, "description": "FORBIDDEN_ROLE / CANNOT_MODIFY_ROOT / CANNOT_MODIFY_SELF / ACCOUNT_DISABLED"},
    },
)

_NOT_FOUND = {404: {"model": ErrorOut, "description": "USER_NOT_FOUND"}}


@router.get("", response_model=UserListOut)
async def list_users(
    _: AdminDep,
    usecase: UserManagementUseCaseDep,
    role: Role | None = None,
    status_: Annotated[Status | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=100, description="Khớp một phần email hoặc tên")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    result = await usecase.list_users(role, status_, q, page, page_size)
    return UserListOut(
        items=[UserAdminOut.model_validate(u) for u in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/{user_id}", response_model=UserAdminOut, responses=_NOT_FOUND)
async def get_user(user_id: int, _: AdminDep, usecase: UserManagementUseCaseDep):
    try:
        return await usecase.get_user(user_id)
    except AuthError as e:
        raise to_api_error(e) from None


@router.post(
    "",
    response_model=UserAdminOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorOut, "description": "EMAIL_TAKEN"}},
)
async def create_user(body: UserCreateIn, current: AdminDep, usecase: UserManagementUseCaseDep):
    """Tạo học sinh (mọi admin) hoặc admin (chỉ admin gốc)."""
    try:
        return await usecase.create_user(current, body.email, body.password, body.role, body.display_name)
    except AuthError as e:
        raise to_api_error(e) from None


@router.patch(
    "/{user_id}",
    response_model=UserAdminOut,
    responses={**_NOT_FOUND, 409: {"model": ErrorOut, "description": "EMAIL_TAKEN"}},
)
async def update_user(user_id: int, body: UserUpdateIn, current: AdminDep, usecase: UserManagementUseCaseDep):
    """Sửa tên, email, vai trò, trạng thái. Khoá (status=disabled) hoặc hạ vai trò thì mọi phiên và socket bị ngắt."""
    try:
        return await usecase.update_user(current, user_id, body.changes())
    except AuthError as e:
        raise to_api_error(e) from None


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT, responses=_NOT_FOUND)
async def reset_password(
    user_id: int, body: ResetPasswordIn, current: AdminDep, usecase: UserManagementUseCaseDep
) -> Response:
    """Đặt mật khẩu mới; mọi phiên và socket của tài khoản đó bị ngắt."""
    try:
        await usecase.reset_password(current, user_id, body.password)
    except AuthError as e:
        raise to_api_error(e) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
