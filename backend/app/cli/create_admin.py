"""Tạo tài khoản admin. Cách duy nhất để có admin (đăng ký công khai chỉ tạo student).

Chạy trong thư mục backend/ (đọc DATABASE_URL từ backend/.env hoặc biến môi trường):

    python -m app.cli.create_admin --email admin@example.com [--name "Quản trị"]

Mật khẩu lấy từ biến ADMIN_PASSWORD, nếu không có thì hỏi qua getpass (nhập hai lần).
Không nhận mật khẩu qua tham số dòng lệnh để mật khẩu không nằm trong lịch sử shell.
Mã thoát: 0 tạo xong · 1 email đã có tài khoản (không tạo trùng) · 2 dữ liệu vào sai.
"""
import argparse
import asyncio
import getpass
import os
import sys
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_engine, get_session
from app.models.user import ROLE_ADMIN
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.service.password_service import PasswordService
from app.service.token_service import TokenService
from app.usecase.auth import AuthUseCase, EmailAlreadyRegistered, InvalidInput, normalize_email

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]

_email = TypeAdapter(EmailStr)


@asynccontextmanager
async def _default_session() -> AsyncIterator[AsyncSession]:
    try:
        async for session in get_session():
            yield session
    finally:
        await get_engine().dispose()


def _read_password() -> str | None:
    env = os.environ.get("ADMIN_PASSWORD")
    if env:
        return env
    if not sys.stdin.isatty():
        print("Không có ADMIN_PASSWORD và không nhập được mật khẩu (stdin không phải terminal).", file=sys.stderr)
        return None
    first = getpass.getpass("Mật khẩu admin: ")
    if getpass.getpass("Nhập lại mật khẩu: ") != first:
        print("Hai lần nhập không khớp.", file=sys.stderr)
        return None
    return first


async def _create(email: str, password: str, name: str | None, session_factory: SessionFactory) -> int:
    async with session_factory() as session:
        usecase = AuthUseCase(
            users=UserRepository(session),
            sessions=SessionRepository(session),
            passwords=PasswordService(),
            tokens=TokenService(),
            session_ttl_hours=get_settings().session_ttl_hours,
        )
        try:
            user = await usecase.create_user(email, password, ROLE_ADMIN, name)
        except EmailAlreadyRegistered:
            print(f"Email {email} đã có tài khoản. Không tạo trùng, không đổi vai trò hay mật khẩu.", file=sys.stderr)
            return 1
        except InvalidInput as e:
            print(e.message, file=sys.stderr)
            return 2
    print(f"Đã tạo admin user_id={user.user_id} email={user.email}")
    return 0


def main(argv: list[str] | None = None, session_factory: SessionFactory | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli.create_admin", description="Tạo tài khoản admin.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default=None, help="Tên hiển thị (tùy chọn, tối đa 100 ký tự)")
    args = parser.parse_args(argv)

    try:
        email = normalize_email(str(_email.validate_python(args.email.strip())))
    except ValidationError:
        print(f"Email không hợp lệ: {args.email}", file=sys.stderr)
        return 2
    name = (args.name or "").strip() or None
    if name and len(name) > 100:
        print("Tên hiển thị tối đa 100 ký tự.", file=sys.stderr)
        return 2

    password = _read_password()
    if password is None:
        return 2
    return asyncio.run(_create(email, password, name, session_factory or _default_session))


if __name__ == "__main__":
    # Console Windows mặc định cp1252, không in được tiếng Việt.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
