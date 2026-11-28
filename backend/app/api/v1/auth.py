from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.cookies import clear_session_cookie, set_session_cookie
from app.api.deps import AuthUseCaseDep, CurrentUserDep, SettingsDep, StudentAuthDep, get_session_token
from app.api.errors import to_api_error
from app.service.socket_tickets import TICKET_TTL_SECONDS
from app.schemas.auth import (
    ErrorOut,
    LoginIn,
    OtpChallengeOut,
    OtpIn,
    OtpResendIn,
    PasswordForgotIn,
    PasswordResetIn,
    PasswordVerifyIn,
    RegisterIn,
    ResetTokenOut,
    UserOut,
)
from app.usecase.auth import AuthError
from app.usecase.student_auth import REGISTRATION

router = APIRouter(prefix="/auth", tags=["auth"])

_SESSION_ERRORS = {
    401: {"model": ErrorOut, "description": "SESSION_MISSING / SESSION_INVALID / SESSION_EXPIRED / SESSION_REVOKED"},
    403: {"model": ErrorOut, "description": "ACCOUNT_DISABLED"},
}


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post(
    "/register",
    response_model=OtpChallengeOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {"model": ErrorOut, "description": "EMAIL_TAKEN"}},
)
async def register(body: RegisterIn, response: Response, student: StudentAuthDep):
    """Yêu cầu mã xác minh để đăng ký học sinh."""
    try:
        pending = await student.start_registration(body.email, body.password, body.display_name)
    except AuthError as error:
        raise to_api_error(error) from None
    _no_store(response)
    return OtpChallengeOut.model_validate(pending)


@router.post("/otp/resend", response_model=OtpChallengeOut, status_code=status.HTTP_202_ACCEPTED)
async def resend_otp(body: OtpResendIn, student: StudentAuthDep, response: Response):
    try:
        pending = await student.resend(body.purpose, body.challenge)
    except AuthError as error:
        raise to_api_error(error) from None
    _no_store(response)
    return OtpChallengeOut.model_validate(pending)


@router.post("/otp/verify", response_model=UserOut, responses={201: {"model": UserOut}})
async def verify_otp(body: OtpIn, request: Request, response: Response, student: StudentAuthDep, settings: SettingsDep):
    try:
        user, token = await student.verify_email(
            body.purpose, body.challenge, body.otp, request.headers.get("user-agent")
        )
    except AuthError as error:
        raise to_api_error(error) from None
    set_session_cookie(response, token, settings)
    _no_store(response)
    if body.purpose == REGISTRATION:
        response.status_code = status.HTTP_201_CREATED
    return user


@router.post(
    "/login",
    response_model=UserOut,
    responses={
        401: {"model": ErrorOut, "description": "INVALID_CREDENTIALS"},
        403: {"model": ErrorOut, "description": "ACCOUNT_DISABLED"},
    },
)
async def login(body: LoginIn, request: Request, response: Response, usecase: AuthUseCaseDep, settings: SettingsDep):
    try:
        user, token = await usecase.login(body.email, body.password, request.headers.get("user-agent"))
    except AuthError as e:
        raise to_api_error(e) from None
    set_session_cookie(response, token, settings)
    _no_store(response)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    usecase: AuthUseCaseDep,
    settings: SettingsDep,
    token: Annotated[str | None, Depends(get_session_token)],
) -> Response:
    """Idempotent: luôn 204 và xoá cookie, kể cả khi không có phiên hoặc phiên đã hết hạn, đã thu hồi,
    không hợp lệ. Thu hồi phiên ngay nếu nó còn."""
    await usecase.logout(token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, settings)
    return response


@router.post("/socket-ticket", responses=_SESSION_ERRORS)
async def socket_ticket(current: CurrentUserDep, request: Request, response: Response):
    _no_store(response)
    return {
        "ticket": request.app.state.realtime.tickets.issue(current.session_id),
        "expires_in": TICKET_TTL_SECONDS,
    }


@router.get("/me", response_model=UserOut, responses=_SESSION_ERRORS)
async def me(current: CurrentUserDep, response: Response):
    _no_store(response)
    return current.user


@router.post(
    "/password/forgot",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        429: {"model": ErrorOut, "description": "OTP_RESEND_LIMIT"},
        503: {"model": ErrorOut, "description": "EMAIL_UNAVAILABLE"},
    },
)
async def forgot_password(body: PasswordForgotIn, student: StudentAuthDep) -> Response:
    """Gửi mã OTP đặt lại mật khẩu. Luôn 204 kể cả khi email chưa có tài khoản."""
    try:
        await student.start_password_reset(body.email)
    except AuthError as error:
        raise to_api_error(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"Cache-Control": "no-store"})


@router.post(
    "/password/verify-otp",
    response_model=ResetTokenOut,
    responses={
        400: {"model": ErrorOut, "description": "OTP_INVALID / OTP_EXPIRED"},
        429: {"model": ErrorOut, "description": "TOO_MANY_ATTEMPTS"},
    },
)
async def verify_password_otp(body: PasswordVerifyIn, student: StudentAuthDep, response: Response):
    try:
        token = await student.verify_password_reset(body.email, body.otp)
    except AuthError as error:
        raise to_api_error(error) from None
    _no_store(response)
    return ResetTokenOut(reset_token=token)


@router.post(
    "/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={400: {"model": ErrorOut, "description": "RESET_TOKEN_INVALID"}},
)
async def reset_password(body: PasswordResetIn, student: StudentAuthDep) -> Response:
    """Đặt mật khẩu mới và thu hồi mọi phiên cũ. Không mở phiên mới: người dùng đăng nhập lại."""
    try:
        await student.reset_password(body.reset_token, body.password)
    except AuthError as error:
        raise to_api_error(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"Cache-Control": "no-store"})
