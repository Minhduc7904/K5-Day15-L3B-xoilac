"""Thống kê cho admin (#20). Mọi route cần AdminDep: khách 401, học sinh 403 FORBIDDEN_ROLE."""
from dataclasses import asdict
from enum import IntEnum
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import AdminAnalyticsDep, AdminDep, OnlineStatsUseCaseDep, require_role
from app.schemas.admin_analytics import BankOut, GrowthOut, LearningOut, OperationsOut, OverviewOut
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


class Days(IntEnum):
    """Khoảng thời gian cho các API phân tích: 7, 30 hoặc 90 ngày gần nhất (ngày tính theo giờ Việt Nam)."""

    WEEK = 7
    MONTH = 30
    QUARTER = 90


# IntEnum (không dùng Literal[7, 30, 90]) vì query string là chuỗi "30" và Literal không tự ép về số.
RangeDays = Annotated[Days, Query(alias="range", description="Số ngày gần nhất")]


@router.get("/overview", response_model=OverviewOut)
async def overview(_: AdminDep, analytics: AdminAnalyticsDep, days: RangeDays = Days.MONTH):
    """Sáu chỉ số đầu trang (kèm kỳ trước và chuỗi theo ngày) và số việc cần chú ý."""
    return await analytics.overview(days)


@router.get("/growth", response_model=GrowthOut)
async def growth(_: AdminDep, analytics: AdminAnalyticsDep, days: RangeDays = Days.MONTH):
    """Đăng ký mới, học sinh hoạt động (ngày/7 ngày), phễu kích hoạt, giờ học cao điểm, cơ cấu khối và mục tiêu."""
    return await analytics.growth(days)


@router.get("/learning", response_model=LearningOut)
async def learning(_: AdminDep, analytics: AdminAnalyticsDep, days: RangeDays = Days.MONTH):
    """Phân bố điểm, điểm theo tuần, cách kết thúc bài, 10 chương tỉ lệ đúng thấp nhất."""
    return await analytics.learning(days)


@router.get("/bank", response_model=BankOut)
async def bank(_: AdminDep, analytics: AdminAnalyticsDep, days: RangeDays = Days.MONTH):
    """Tình trạng ngân hàng câu hỏi: trạng thái, độ phủ chương × độ khó, chương học sinh cần mà thiếu câu."""
    return await analytics.bank(days)


@router.get("/operations", response_model=OperationsOut)
async def operations(_: AdminDep, analytics: AdminAnalyticsDep, days: RangeDays = Days.MONTH):
    """Nhập đề PDF, credit cấp/tiêu, phiên chat tạo đề và tỉ lệ đi tới làm bài."""
    return await analytics.operations(days)
