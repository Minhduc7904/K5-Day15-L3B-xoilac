from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import NotificationsDep, StudentDep
from app.api.errors import ApiError
from app.schemas.notification import NotificationsOut
from app.usecase.notifications import NotFound


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/student/me/notifications", tags=["notifications"], dependencies=[Depends(no_store)])


@router.get("", response_model=NotificationsOut)
async def list_notifications(
    user: StudentDep, usecase: NotificationsDep,
    before_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return await usecase.list(user.user_id, before_id, limit)


@router.post("/read-all", status_code=204)
async def read_all(user: StudentDep, usecase: NotificationsDep):
    await usecase.read_all(user.user_id)


@router.post("/{notification_id}/read", status_code=204)
async def read_one(notification_id: int, user: StudentDep, usecase: NotificationsDep):
    try:
        await usecase.read(user.user_id, notification_id)
    except NotFound:
        raise ApiError(404, "NOTIFICATION_NOT_FOUND", "Không tìm thấy thông báo") from None
