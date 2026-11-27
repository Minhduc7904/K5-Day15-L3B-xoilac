"""Test lệnh `python -m app.cli.create_admin`. Test đồng bộ vì lệnh tự gọi asyncio.run."""
import asyncio
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.cli.create_admin import main
from app.models import Base, User
from app.service.password_service import PasswordService
from tests.conftest import new_password

PW = new_password()  # sinh lúc chạy, không viết cứng


@pytest.fixture
def db_url(tmp_path):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'cli.db').as_posix()}"

    async def _init():
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_init())
    return url


def _factory(url):
    @asynccontextmanager
    async def _session():
        engine = create_async_engine(url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as s:
                yield s
        finally:
            await engine.dispose()

    return _session


def _users(url):
    async def _q():
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            rows = (await conn.execute(select(User.email, User.role, User.password_hash))).all()
        await engine.dispose()
        return rows

    return asyncio.run(_q())


def test_create_admin_and_no_duplicate(db_url, monkeypatch, capsys):
    monkeypatch.setenv("ADMIN_PASSWORD", PW)

    assert main(["--email", " Admin@Example.com ", "--name", "Quản trị"], session_factory=_factory(db_url)) == 0
    out = capsys.readouterr()
    assert "admin@example.com" in out.out
    assert PW not in out.out + out.err

    # Chạy lại cùng email (khác hoa/thường): báo rõ, không tạo trùng.
    assert main(["--email", "ADMIN@example.com"], session_factory=_factory(db_url)) == 1
    assert "đã có tài khoản" in capsys.readouterr().err

    rows = _users(db_url)
    assert len(rows) == 1
    email, role, password_hash = rows[0]
    assert (email, role) == ("admin@example.com", "admin")
    assert password_hash.startswith("$argon2id$") and PW not in password_hash
    assert asyncio.run(PasswordService().verify(password_hash, PW))


def test_create_admin_rejects_bad_input(db_url, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "x" * 5)
    assert main(["--email", "admin@example.com"], session_factory=_factory(db_url)) == 2  # mật khẩu < 6
    monkeypatch.setenv("ADMIN_PASSWORD", PW)
    assert main(["--email", "khong-phai-email"], session_factory=_factory(db_url)) == 2
    assert _users(db_url) == []


def test_create_admin_has_no_password_argument():
    with pytest.raises(SystemExit):
        main(["--email", "admin@example.com", "--password", PW])
