from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.cookies import set_session_cookie
from app.api.deps import GoogleIdentityDep, SettingsDep, StudentAuthDep
from app.api.errors import to_api_error
from app.schemas.auth import GoogleExchangeIn, GoogleStartIn, GoogleStartOut, OtpChallengeOut, UserOut
from app.service.google_identity import GoogleConfigurationError, GoogleIdentityError
from app.usecase.auth import AuthError
from app.usecase.student_auth import PendingVerification

router = APIRouter(prefix="/auth/google", tags=["auth"])
callback_router = APIRouter(include_in_schema=False)
_NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


@router.post("/start", response_model=GoogleStartOut)
async def start(body: GoogleStartIn, google: GoogleIdentityDep, response: Response):
    try:
        url = google.authorization_url(body.challenge)
    except GoogleConfigurationError:
        return JSONResponse(
            {"detail": "Đăng nhập Google chưa được bật.", "code": "GOOGLE_UNAVAILABLE"},
            status_code=503,
            headers=_NO_STORE,
        )
    response.headers.update(_NO_STORE)
    return GoogleStartOut(url=url)


@callback_router.get("/api/auth/google/callback")
async def callback(
    google: GoogleIdentityDep,
    student: StudentAuthDep,
    settings: SettingsDep,
    code: Annotated[str | None, Query(max_length=2048)] = None,
    state: Annotated[str | None, Query(max_length=512)] = None,
):
    if not google.enabled:
        return Response(status_code=503, headers=_NO_STORE)
    frontend = settings.frontend_url.rstrip("/") + "/login/google"
    result = "#error=google"
    if code and state:
        try:
            identity, browser_challenge = await google.verify_callback(code, state)
            ticket = await student.save_google_handoff(identity, browser_challenge)
            result = f"#ticket={ticket}"
        except GoogleIdentityError:
            pass
    return RedirectResponse(frontend + result, status_code=303, headers=_NO_STORE)


@router.post("/exchange", response_model=UserOut | OtpChallengeOut)
async def exchange(
    body: GoogleExchangeIn, student: StudentAuthDep, request: Request, response: Response, settings: SettingsDep
):
    response.headers.update(_NO_STORE)
    try:
        result = await student.exchange_google_handoff(body.ticket, body.verifier, request.headers.get("user-agent"))
    except AuthError as error:
        raise to_api_error(error) from None
    if isinstance(result, PendingVerification):
        response.status_code = 202
        return OtpChallengeOut.model_validate(result)
    user, token = result
    set_session_cookie(response, token, settings)
    return user
