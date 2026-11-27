"""Admin quản lý tài khoản admin. Mọi route cần AdminDep: khách 401, student 403 FORBIDDEN_ROLE.

Thao tác cấp hoặc đổi quyền (tạo admin, khoá/mở khoá) đòi `current_password` của admin đang thao tác.
"""
from fastapi import APIRouter, Depends, status

from app.api.deps import AdminAccountsUseCaseDep, AdminDep, require_role
from app.api.errors import to_api_error
from app.schemas.admin_accounts import AdminAccountOut, AdminCreateIn, AdminStatusIn
from app.schemas.auth import ErrorOut
from app.usecase.auth import AuthError

router = APIRouter(
    prefix="/admin/accounts",
    tags=["admin"],
    dependencies=[Depends(require_role("admin"))],
    responses={
        401: {"model": ErrorOut, "description": "SESSION_* (mất phiên) hoặc REAUTH_FAILED (sai mật khẩu xác nhận)"},
        403: {"model": ErrorOut, "description": "FORBIDDEN_ROLE / ACCOUNT_DISABLED"},
    },
)


@router.get("", response_model=list[AdminAccountOut])
async def list_admins(_: AdminDep, usecase: AdminAccountsUseCaseDep):
    return await usecase.list_admins()


@router.post(
    "",
    response_model=AdminAccountOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorOut, "description": "EMAIL_TAKEN (kể cả email của student)"}},
)
async def create_admin(body: AdminCreateIn, current: AdminDep, usecase: AdminAccountsUseCaseDep):
    try:
        return await usecase.create_admin(current, body.email, body.password, body.display_name, body.current_password)
    except AuthError as e:
        raise to_api_error(e) from None


@router.patch(
    "/{user_id}/status",
    response_model=AdminAccountOut,
    responses={
        404: {"model": ErrorOut, "description": "ACCOUNT_NOT_FOUND (không có hoặc không phải admin)"},
        409: {"model": ErrorOut, "description": "CANNOT_MODIFY_SELF / LAST_ADMIN"},
    },
)
async def set_status(user_id: int, body: AdminStatusIn, current: AdminDep, usecase: AdminAccountsUseCaseDep):
    """Khoá (`disabled`) thì mọi phiên của tài khoản đó bị thu hồi ngay. Mở khoá thì họ phải đăng nhập lại."""
    try:
        return await usecase.set_status(current, user_id, body.status, body.current_password)
    except AuthError as e:
        raise to_api_error(e) from None
