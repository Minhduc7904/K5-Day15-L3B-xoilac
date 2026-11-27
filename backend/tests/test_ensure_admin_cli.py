"""Test phần A: `python -m app.cli.ensure_admin` (admin mặc định khi khởi động).

Test đồng bộ vì lệnh tự gọi asyncio.run; dùng SQLite dạng file để mỗi lần chạy mở engine riêng.
"""
import asyncio
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.cli.ensure_admin import main
from app.core.config import Settings
from app.models import Base, User
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.service.password_service import PasswordService
from app.service.token_service import TokenService
from app.usecase.auth import AuthUseCase, InvalidCredentials
from tests.conftest import new_password

# Sinh lúc chạy, không viết cứng (tests/conftest.py).
PW = new_password()
PW_OTHER = new_password()


@pytest.fixture
def db_url(tmp_path):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'ensure.db').as_posix()}"

    async def _init():
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_init())
    return url


@asynccontextmanager
async def _session(url):
    engine = create_async_engine(url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as s:
            yield s
    finally:
        await engine.dispose()


def _factory(url):
    return lambda: _session(url)


def _settings(email="admin@example.com", password=PW, name="Quản trị", secure=False) -> Settings:
    return Settings(_env_file=None, admin_email=email, admin_password=password, admin_name=name, cookie_secure=secure)


def _run(url, **kw) -> int:
    return main(settings=_settings(**kw), session_factory=_factory(url))


def _users(url):
    async def _q():
        async with _session(url) as s:
            return (await s.execute(select(User).order_by(User.user_id))).scalars().all()

    return asyncio.run(_q())


def _login(url, email, password):
    async def _q():
        async with _session(url) as s:
            uc = AuthUseCase(UserRepository(s), SessionRepository(s), PasswordService(), TokenService(), 168)
            user, _ = await uc.login(email, password)
            return user

    return asyncio.run(_q())


@pytest.mark.parametrize(("email", "password"), [("", PW), ("admin@example.com", ""), ("  ", "")])
def test_missing_vars_skips_with_exit_0(db_url, capsys, email, password):
    assert _run(db_url, email=email, password=password) == 0
    assert "Bỏ qua tạo admin mặc định: thiếu ADMIN_EMAIL/ADMIN_PASSWORD" in capsys.readouterr().out
    assert _users(db_url) == []


def test_creates_admin_that_can_log_in(db_url, capsys):
    assert _run(db_url, email="  Admin@Example.COM ") == 0
    assert "Đã tạo admin mặc định" in capsys.readouterr().out

    [user] = _users(db_url)
    assert (user.email, user.role, user.status, user.created_by) == ("admin@example.com", "admin", "active", None)
    assert user.display_name == "Quản trị"
    assert _login(db_url, "admin@example.com", PW).role == "admin"


def test_second_run_does_not_duplicate(db_url, capsys):
    assert _run(db_url) == 0
    assert _run(db_url) == 0
    assert "Admin mặc định đã có, không thay đổi" in capsys.readouterr().out
    assert len(_users(db_url)) == 1


def test_existing_admin_keeps_old_password_and_status(db_url):
    assert _run(db_url) == 0

    async def _disable():
        async with _session(db_url) as s:
            await s.execute(update(User).values(status="disabled"))
            await s.commit()

    asyncio.run(_disable())
    # Chạy lại với mật khẩu khác: không ghi đè mật khẩu, không mở khoá.
    assert _run(db_url, password=PW_OTHER) == 0
    [user] = _users(db_url)
    assert user.status == "disabled"
    assert asyncio.run(PasswordService().verify(user.password_hash, PW))
    assert not asyncio.run(PasswordService().verify(user.password_hash, PW_OTHER))


def test_existing_admin_new_password_cannot_log_in(db_url):
    assert _run(db_url) == 0
    assert _run(db_url, password=PW_OTHER) == 0
    with pytest.raises(InvalidCredentials):
        _login(db_url, "admin@example.com", PW_OTHER)
    assert _login(db_url, "admin@example.com", PW).role == "admin"


def test_student_email_warns_exit_0_and_is_not_promoted(db_url, capsys):
    async def _student():
        async with _session(db_url) as s:
            uc = AuthUseCase(UserRepository(s), SessionRepository(s), PasswordService(), TokenService(), 168)
            await uc.create_user("hs01@example.com", new_password(), "student")

    asyncio.run(_student())
    before = _users(db_url)[0]
    # Mã 0: db-init không fail. Không đổi vai trò, mật khẩu hay status.
    assert _run(db_url, email="HS01@example.com") == 0
    assert "không nâng quyền" in capsys.readouterr().err
    [user] = _users(db_url)
    assert (user.role, user.status, user.password_hash) == ("student", before.status, before.password_hash)


def test_prod_requires_12_chars(db_url, capsys):
    assert _run(db_url, password="x" * 11, secure=True) == 2
    assert "ít nhất 12 ký tự" in capsys.readouterr().err
    assert _users(db_url) == []
    assert _run(db_url, password="x" * 12, secure=True) == 0
    assert len(_users(db_url)) == 1


@pytest.mark.parametrize("password", ["x" * 7, "x" * 129])
def test_password_length_rule(db_url, password):
    assert _run(db_url, password=password) == 2
    assert _users(db_url) == []


def test_invalid_email(db_url):
    assert _run(db_url, email="admin@examind.local") == 2
    assert _users(db_url) == []


def test_output_never_contains_password(db_url, capsys):
    _run(db_url)
    _run(db_url, password=PW_OTHER)
    too_short = new_password()[:11]  # < 12 ký tự: lỗi prod, vẫn không được in ra
    _run(db_url, password=too_short, secure=True)
    out = capsys.readouterr()
    for secret in (PW, PW_OTHER, too_short, "$argon2"):
        assert secret not in out.out + out.err


# ---- Admin gốc (#20) ------------------------------------------------------------


def _make_admin(url, email):
    async def _q():
        async with _session(url) as s:
            uc = AuthUseCase(UserRepository(s), SessionRepository(s), PasswordService(), TokenService(), 168)
            await uc.create_user(email, PW, "admin")

    asyncio.run(_q())


def _by_email(url):
    return {u.email: u for u in _users(url)}


def test_created_admin_is_root(db_url):
    assert _run(db_url) == 0
    [user] = _users(db_url)
    assert user.is_root is True


def test_existing_plain_admin_is_marked_root_without_password_change(db_url, capsys):
    _make_admin(db_url, "admin@example.com")
    before = _by_email(db_url)["admin@example.com"]
    assert before.is_root is False

    assert _run(db_url, password=PW_OTHER) == 0
    assert "đánh dấu làm admin gốc" in capsys.readouterr().out
    after = _by_email(db_url)["admin@example.com"]
    assert after.is_root is True
    assert after.password_hash == before.password_hash  # không đổi mật khẩu
    # Chạy lại: giữ nguyên, vẫn một admin gốc.
    assert _run(db_url) == 0
    assert [u.email for u in _users(db_url) if u.is_root] == ["admin@example.com"]


def test_other_root_exists_new_email_is_not_created(db_url, capsys):
    assert _run(db_url) == 0  # admin@example.com là gốc
    capsys.readouterr()
    assert _run(db_url, email="admin2@example.com") == 0
    assert "đã có admin gốc khác" in capsys.readouterr().err
    assert set(_by_email(db_url)) == {"admin@example.com"}


def test_other_root_exists_plain_admin_is_not_marked(db_url, capsys):
    assert _run(db_url) == 0
    _make_admin(db_url, "admin2@example.com")
    capsys.readouterr()
    assert _run(db_url, email="admin2@example.com") == 0
    assert "đã có admin gốc khác" in capsys.readouterr().err
    users = _by_email(db_url)
    assert users["admin@example.com"].is_root is True
    assert users["admin2@example.com"].is_root is False


def test_database_allows_at_most_one_root_and_root_must_be_admin(db_url):
    from sqlalchemy.exc import IntegrityError

    assert _run(db_url) == 0
    _make_admin(db_url, "admin2@example.com")

    async def _try(sql):
        async with _session(db_url) as s:
            await s.execute(text(sql))
            await s.commit()

    with pytest.raises(IntegrityError):
        asyncio.run(_try("UPDATE users SET is_root = 1 WHERE email = 'admin2@example.com'"))
    with pytest.raises(IntegrityError):
        asyncio.run(_try("UPDATE users SET role = 'student' WHERE email = 'admin@example.com'"))
