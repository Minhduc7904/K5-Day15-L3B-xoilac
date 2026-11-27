"""Đổi lỗi nghiệp vụ thành HTTP. Body lỗi: {"detail": "<thông báo>", "code": "<MÃ>"}.

Lỗi 422 do FastAPI kiểm schema giữ định dạng mặc định (`detail` là danh sách lỗi theo trường).
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.api.cookies import clear_session_cookie
from app.core.config import get_settings
from app.usecase.auth import (
    AccountDisabled,
    AuthError,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidInput,
    RoleForbidden,
    SessionExpired,
    SessionInvalid,
    SessionMissing,
    SessionRevoked,
)

_STATUS: dict[type[AuthError], int] = {
    EmailAlreadyRegistered: status.HTTP_409_CONFLICT,
    InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
    AccountDisabled: status.HTTP_403_FORBIDDEN,
    SessionMissing: status.HTTP_401_UNAUTHORIZED,
    SessionInvalid: status.HTTP_401_UNAUTHORIZED,
    SessionExpired: status.HTTP_401_UNAUTHORIZED,
    SessionRevoked: status.HTTP_401_UNAUTHORIZED,
    RoleForbidden: status.HTTP_403_FORBIDDEN,
    InvalidInput: 422,
}

# Phiên trong cookie không còn dùng được: xoá cookie để trình duyệt khỏi gửi lại.
_CLEAR_COOKIE = (SessionInvalid, SessionExpired, SessionRevoked, AccountDisabled)


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, detail: str, clear_cookie: bool = False) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.clear_cookie = clear_cookie


def to_api_error(e: AuthError, *, in_session_check: bool = False) -> ApiError:
    return ApiError(
        status_code=_STATUS.get(type(e), status.HTTP_400_BAD_REQUEST),
        code=e.code,
        detail=e.message,
        clear_cookie=in_session_check and isinstance(e, _CLEAR_COOKIE),
    )


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    response = JSONResponse({"detail": exc.detail, "code": exc.code}, status_code=exc.status_code)
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        response.headers["WWW-Authenticate"] = "Bearer"
    if exc.clear_cookie:
        # Handler nằm ngoài hệ dependency nên tự lấy settings, có tính override của test.
        settings = request.app.dependency_overrides.get(get_settings, get_settings)()
        clear_session_cookie(response, settings)
    return response
