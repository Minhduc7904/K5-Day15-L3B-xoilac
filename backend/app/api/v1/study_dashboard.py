from fastapi import APIRouter, Depends, Response

from app.api.deps import StudentDashboardDep, StudentDep
from app.schemas.study import DashboardOut


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/study", tags=["study-dashboard"], dependencies=[Depends(no_store)])


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(user: StudentDep, usecase: StudentDashboardDep):
    return await usecase.get(user.user_id)
