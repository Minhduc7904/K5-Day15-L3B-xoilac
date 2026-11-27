"""Tạo tài khoản admin bằng tay. Dùng để CỨU HỘ khi mọi admin đều mất quyền truy cập.

Cách thường dùng: admin mặc định do `ensure_admin` tạo lúc khởi động, rồi admin tạo admin khác qua API
(xem docs/architecture/backend-auth.md, mục "Cấp tài khoản admin").

Chạy trong thư mục backend/ (đọc DATABASE_URL từ backend/.env hoặc biến môi trường):

    python -m app.cli.create_admin --email admin2@example.com [--name "Quản trị"]

Mật khẩu lấy từ biến ADMIN_PASSWORD, nếu không có thì hỏi qua getpass (nhập hai lần).
Không nhận mật khẩu qua tham số dòng lệnh để mật khẩu không nằm trong lịch sử shell.
Mã thoát: 0 tạo xong · 1 email đã có tài khoản (không tạo trùng) · 2 dữ liệu vào sai.
"""
import argparse
import asyncio
import getpass
import os
import sys

from app.cli.common import NAME_MAX, SessionFactory, build_auth, default_session, utf8_console, validate_email
from app.core.config import get_settings
from app.models.user import ROLE_ADMIN
from app.usecase.auth import EmailAlreadyRegistered, InvalidInput


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
        try:
            user = await build_auth(session, get_settings()).create_user(email, password, ROLE_ADMIN, name)
        except EmailAlreadyRegistered:
            print(f"Email {email} đã có tài khoản. Không tạo trùng, không đổi vai trò hay mật khẩu.", file=sys.stderr)
            return 1
        except InvalidInput as e:
            print(e.message, file=sys.stderr)
            return 2
    print(f"Đã tạo admin user_id={user.user_id} email={user.email}")
    return 0


def main(argv: list[str] | None = None, session_factory: SessionFactory | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli.create_admin", description="Tạo tài khoản admin (cứu hộ).")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default=None, help=f"Tên hiển thị (tùy chọn, tối đa {NAME_MAX} ký tự)")
    args = parser.parse_args(argv)

    email = validate_email(args.email)
    if email is None:
        print(f"Email không hợp lệ: {args.email}", file=sys.stderr)
        return 2
    name = (args.name or "").strip() or None
    if name and len(name) > NAME_MAX:
        print(f"Tên hiển thị tối đa {NAME_MAX} ký tự.", file=sys.stderr)
        return 2

    password = _read_password()
    if password is None:
        return 2
    return asyncio.run(_create(email, password, name, session_factory or default_session))


if __name__ == "__main__":
    utf8_console()
    sys.exit(main())
