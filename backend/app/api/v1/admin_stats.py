"""Thống kê cho admin (#20). Mọi route cần AdminDep: khách 401, học sinh 403 FORBIDDEN_ROLE."""
from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import AdminDep, OnlineStatsUseCaseDep, require_role
from app.schemas.admin_stats import OnlineStatsOut
from app.schemas.auth import ErrorOut

router = APIRouter(
    prefix="/admin/stats",
    tags=["admin"],
    dependencies=[Depends(require_role("admin"))],
    responses={
        401: {"model": ErrorOut, "description": "SESSION_*"},
        403: {"model": ErrorOut, "description": "FORBIDDEN_ROLE / ACCOUNT_DISABLED"},
    },
)


@router.get("/online-students", response_model=OnlineStatsOut, response_model_exclude_unset=True)
async def online_students(
    _: AdminDep,
    usecase: OnlineStatsUseCaseDep,
    include: Annotated[Literal["users"] | None, Query(description="users: kèm danh sách học sinh online")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """Số học sinh có ít nhất một kết nối socket sống và tổng số kết nối của họ (nhiều tab = 1 học sinh)."""
    stats = await usecase.online_students(include_users=include == "users", page=page, page_size=page_size)
    # Chỉ đặt users/page/page_size khi có ?include=users; exclude_unset bỏ chúng khỏi body khi không có.
    # (Không dùng exclude_none: sẽ làm mất display_name null của từng học sinh.)
    return OnlineStatsOut(**{k: v for k, v in asdict(stats).items() if v is not None})
