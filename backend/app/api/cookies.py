"""Cookie phiên tách riêng theo vai trò để admin và học sinh đăng nhập song song trong cùng một trình duyệt.

- Học sinh dùng `settings.cookie_name`, admin dùng `settings.admin_cookie_name`.
- Đăng nhập chọn cookie theo vai trò của tài khoản.
- Khi đọc phiên, frontend gửi header `X-Auth-Scope: admin | student` (admin cho các trang /admin). Không có header
  (curl, Swagger, test) thì ưu tiên cookie học sinh, không có thì dùng cookie admin.
"""
from typing import Literal

from fastapi import Request, Response

from app.core.config import Settings

Scope = Literal["admin", "student"]
SCOPE_HEADER = "x-auth-scope"


def scope_for_role(role: str) -> Scope:
    return "admin" if role == "admin" else "student"


def cookie_name_for(scope: Scope, settings: Settings) -> str:
    return settings.admin_cookie_name if scope == "admin" else settings.cookie_name


def request_scope(request: Request) -> Scope | None:
    """Phạm vi frontend yêu cầu; `None` khi request không khai báo (curl, Swagger, test)."""
    value = request.headers.get(SCOPE_HEADER, "").strip().lower()
    return value if value in ("admin", "student") else None  # type: ignore[return-value]


def session_cookie_name(request: Request, settings: Settings) -> str | None:
    """Tên cookie phiên mà request này đang dùng (có giá trị), hoặc `None`."""
    scope = request_scope(request)
    candidates: list[Scope] = [scope] if scope else ["student", "admin"]
    for candidate in candidates:
        name = cookie_name_for(candidate, settings)
        if request.cookies.get(name):
            return name
    return None


def set_session_cookie(response: Response, token: str, settings: Settings, role: str = "student") -> None:
    response.set_cookie(
        key=cookie_name_for(scope_for_role(role), settings),
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def clear_session_cookie(response: Response, settings: Settings, name: str | None = None) -> None:
    response.delete_cookie(
        key=name or settings.cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
