from typing import Annotated, Awaitable, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import SessionDep, StorageDep, StudentDep
from app.repositories.exam_attempts import ExamAttemptRepository
from app.repositories.question_bank_repository import QuestionBankRepository
from app.schemas.exam_attempt import AttemptSave, AttemptStart
from app.usecase.exam_attempts import AttemptError, ExamAttempts

router = APIRouter(prefix="/study", tags=["exam-attempts"])


def get_attempts(session: SessionDep) -> ExamAttempts:
    return ExamAttempts(ExamAttemptRepository(session), QuestionBankRepository(session))


AttemptsDep = Annotated[ExamAttempts, Depends(get_attempts)]


T = TypeVar("T")


async def respond(response: Response, operation: Awaitable[T]) -> T:
    response.headers["Cache-Control"] = "no-store"
    try:
        return await operation
    except AttemptError as error:
        raise HTTPException(error.status, {"code": error.code, "message": str(error)},
                            headers={"Cache-Control": "no-store"}) from None


@router.get("/attempts")
async def summaries(user: StudentDep, attempts: AttemptsDep, response: Response):
    return await respond(response, attempts.summaries(user.user_id))


@router.get("/exams/{draft_id}/attempts")
async def overview(draft_id: int, user: StudentDep, attempts: AttemptsDep, response: Response):
    return await respond(response, attempts.overview(user.user_id, draft_id))


@router.post("/exams/{draft_id}/attempts")
async def start(draft_id: int, body: AttemptStart, user: StudentDep, attempts: AttemptsDep, response: Response):
    return await respond(response, attempts.start(user.user_id, draft_id, body.restart))


@router.get("/attempts/{attempt_id}")
async def read(attempt_id: int, user: StudentDep, attempts: AttemptsDep, response: Response):
    return await respond(response, attempts.read(user.user_id, attempt_id))


@router.patch("/attempts/{attempt_id}")
async def save(attempt_id: int, body: AttemptSave, user: StudentDep, attempts: AttemptsDep, response: Response):
    return await respond(response, attempts.save(user.user_id, attempt_id, body))


@router.post("/attempts/{attempt_id}/submit")
async def submit(attempt_id: int, user: StudentDep, attempts: AttemptsDep, response: Response):
    return await respond(response, attempts.submit(user.user_id, attempt_id))


@router.get("/attempts/{attempt_id}/result")
async def result(attempt_id: int, user: StudentDep, attempts: AttemptsDep, response: Response):
    return await respond(response, attempts.result(user.user_id, attempt_id))


@router.get("/attempts/{attempt_id}/media/{media_id}")
async def media(attempt_id: int, media_id: int, user: StudentDep, attempts: AttemptsDep, storage: StorageDep,
                response: Response):
    data, mime = await respond(response, attempts.media(user.user_id, attempt_id, media_id, storage))
    return Response(data, media_type=mime, headers={"Cache-Control": "private, no-store",
                                                   "X-Content-Type-Options": "nosniff"})
