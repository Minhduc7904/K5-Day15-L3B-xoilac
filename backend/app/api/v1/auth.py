from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.cookies import clear_session_cookie, set_session_cookie
from app.api.deps import AuthUseCaseDep, CurrentUserDep, RealtimeUseCaseDep, SettingsDep, get_session_token
from app.api.errors import to_api_error
from app.schemas.auth import ErrorOut, LoginIn, RegisterIn, UserOut
from app.schemas.realtime import SocketTicketOut
from app.usecase.auth import AuthError

router = APIRouter(prefix="/auth", tags=["auth"])

_SESSION_ERRORS = {
    401: {"model": ErrorOut, "description": "SESSION_MISSING / SESSION_INVALID / SESSION_EXPIRED / SESSION_REVOKED"},
    403: {"model": ErrorOut, "description": "ACCOUNT_DISABLED"},
}


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorOut, "description": "EMAIL_TAKEN"}},
)
async def register(body: RegisterIn, request: Request, response: Response, usecase: AuthUseCaseDep, settings: SettingsDep):
    """Đăng ký học sinh và đăng nhập luôn (đặt cookie). Trường `role` trong body bị bỏ qua."""
    try:
        user, token = await usecase.register(
            body.email, body.password, body.display_name, request.headers.get("user-agent")
        )
    except AuthError as e:
        raise to_api_error(e) from None
    set_session_cookie(response, token, settings)
    _no_store(response)
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


@router.get("/me", response_model=UserOut, responses=_SESSION_ERRORS)
async def me(current: CurrentUserDep, response: Response):
    _no_store(response)
    return current.user


@router.post("/socket-ticket", response_model=SocketTicketOut, responses=_SESSION_ERRORS)
async def socket_ticket(current: CurrentUserDep, realtime: RealtimeUseCaseDep, response: Response):
    """Ticket một lần, sống `expires_in` giây, để nối Socket.IO bằng `auth: {ticket}` (#20).
    Gắn với người dùng và phiên hiện tại: đăng xuất phiên này thì socket mở bằng ticket của nó bị ngắt."""
    ticket, ttl = realtime.issue_ticket(current)
    _no_store(response)
    return SocketTicketOut(ticket=ticket, expires_in=ttl)
