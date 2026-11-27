"""Endpoint admin. Mẫu áp dụng quyền cho #11: mọi route ở đây phụ thuộc AdminDep."""
from fastapi import APIRouter

from app.api.deps import AdminDep
from app.schemas.auth import AdminPingOut, ErrorOut

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={
        401: {"model": ErrorOut, "description": "Chưa đăng nhập hoặc phiên không còn hiệu lực"},
        403: {"model": ErrorOut, "description": "FORBIDDEN_ROLE / ACCOUNT_DISABLED"},
    },
)


@router.get("/ping", response_model=AdminPingOut)
async def ping(current: AdminDep) -> AdminPingOut:
    return AdminPingOut(status="ok", user_id=current.user_id, role=current.role)
