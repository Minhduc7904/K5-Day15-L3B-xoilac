"""Tạo admin mặc định từ biến môi trường nếu chưa có. Chạy trong container db-init, ngay sau
`alembic upgrade head` (một lần mỗi lần deploy). KHÔNG gọi trong lifespan của FastAPI: nhiều worker
có thể chạy cùng lúc.

    python -m app.cli.ensure_admin

Đọc ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_NAME (tuỳ chọn) và COOKIE_SECURE từ biến môi trường hoặc backend/.env.

| Tình huống | Kết quả | Mã thoát |
| --- | --- | --- |
| Thiếu ADMIN_EMAIL hoặc ADMIN_PASSWORD | Bỏ qua | 0 |
| Chưa có tài khoản với email này | Tạo admin active, created_by = NULL | 0 |
| Email đã là admin | Không đổi gì (không ghi đè mật khẩu, không đổi status) | 0 |
| Email đang thuộc tài khoản không phải admin (student) | Cảnh báo, không đổi mật khẩu, vai trò hay status | 0 |
| Email sai định dạng, mật khẩu sai độ dài, prod mà mật khẩu < 12 ký tự | Báo lỗi | 2 |

Email trùng không làm db-init fail (theo review PR #17): người vận hành chỉ cần đổi ADMIN_EMAIL.
Mật khẩu yếu trên prod thì VẪN fail, để prod không bao giờ chạy với admin mặc định yếu.

Không bao giờ in mật khẩu hay hash.
"""
import asyncio
import sys

from app.cli.common import NAME_MAX, SessionFactory, build_admin_accounts, default_session, utf8_console, validate_email
from app.core.config import Settings, get_settings
from app.usecase.admin_accounts import EmailBelongsToNonAdmin, EnsureResult
from app.usecase.auth import InvalidInput


async def _ensure(email: str, password: str, name: str | None, settings: Settings, factory: SessionFactory) -> int:
    async with factory() as session:
        usecase = build_admin_accounts(session, settings)
        try:
            result, user = await usecase.ensure_default_admin(email, password, name, strict=settings.cookie_secure)
        except EmailBelongsToNonAdmin:
            print(
                f"CẢNH BÁO: {email} đang là tài khoản không phải admin. Bỏ qua tạo admin mặc định: "
                "không nâng quyền, không đổi mật khẩu hay status. Đổi ADMIN_EMAIL sang email khác.",
                file=sys.stderr,
            )
            return 0
        except InvalidInput as e:
            print(f"Lỗi admin mặc định: {e.message}", file=sys.stderr)
            return 2
    if result is EnsureResult.CREATED:
        print(f"Đã tạo admin mặc định user_id={user.user_id} email={user.email}")
    else:
        print(f"Admin mặc định đã có, không thay đổi (user_id={user.user_id} email={user.email})")
    return 0


def main(settings: Settings | None = None, session_factory: SessionFactory | None = None) -> int:
    settings = settings or get_settings()
    raw_email = settings.admin_email.strip()
    password = settings.admin_password.get_secret_value()
    if not raw_email or not password:
        print("Bỏ qua tạo admin mặc định: thiếu ADMIN_EMAIL/ADMIN_PASSWORD")
        return 0

    email = validate_email(raw_email)
    if email is None:
        print(f"Lỗi admin mặc định: ADMIN_EMAIL không hợp lệ: {raw_email}", file=sys.stderr)
        return 2
    name = settings.admin_name.strip() or None
    if name and len(name) > NAME_MAX:
        print(f"Lỗi admin mặc định: ADMIN_NAME tối đa {NAME_MAX} ký tự", file=sys.stderr)
        return 2
    return asyncio.run(_ensure(email, password, name, settings, session_factory or default_session))


if __name__ == "__main__":
    utf8_console()
    sys.exit(main())
