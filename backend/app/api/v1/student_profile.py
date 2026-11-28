from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import StudentDep, StudentProfileDep
from app.api.errors import ApiError
from app.schemas.student import CreditsOut, ProfileIn, ProfileOut, ProfileStatusOut
from app.usecase.student_profile import UnverifiedReminderEmail

def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/student/me", tags=["student-profile"], dependencies=[Depends(no_store)])


@router.get("/profile", response_model=ProfileStatusOut)
async def get_profile(current: StudentDep, usecase: StudentProfileDep):
    return await usecase.get(current.user)


@router.put("/profile", response_model=ProfileOut)
async def save_profile(body: ProfileIn, current: StudentDep, usecase: StudentProfileDep):
    try:
        return await usecase.save(current.user, body)
    except UnverifiedReminderEmail:
        raise ApiError(422, "REMINDER_EMAIL_UNVERIFIED", "Hãy xác minh email trước khi bật nhắc học") from None


@router.get("/credits", response_model=CreditsOut)
async def get_credits(
    current: StudentDep,
    usecase: StudentProfileDep,
    before_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return await usecase.credits(current.user_id, before_id, limit)
