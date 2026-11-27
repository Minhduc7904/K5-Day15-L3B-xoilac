"""Phần dùng chung của các lệnh CLI tài khoản (create_admin, ensure_admin).

CLI là một entry point như API: tự ghép repository, service và usecase ở đây, giống app/api/deps.py.
"""
import sys
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import get_engine, get_session
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.service.password_service import PasswordService
from app.service.token_service import TokenService
from app.usecase.admin_accounts import AdminAccountsUseCase
from app.usecase.auth import AuthUseCase, normalize_email

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]
NAME_MAX = 100

_email = TypeAdapter(EmailStr)


@asynccontextmanager
async def default_session() -> AsyncIterator[AsyncSession]:
    try:
        async for session in get_session():
            yield session
    finally:
        await get_engine().dispose()


def validate_email(raw: str) -> str | None:
    """Cùng luật với RegisterIn: EmailStr, bỏ khoảng trắng hai đầu, chữ thường. Sai định dạng → None."""
    try:
        return normalize_email(str(_email.validate_python(raw.strip())))
    except ValidationError:
        return None


def build_auth(session: AsyncSession, settings: Settings) -> AuthUseCase:
    return AuthUseCase(
        users=UserRepository(session),
        sessions=SessionRepository(session),
        passwords=PasswordService(),
        tokens=TokenService(),
        session_ttl_hours=settings.session_ttl_hours,
    )


def build_admin_accounts(session: AsyncSession, settings: Settings) -> AdminAccountsUseCase:
    users, sessions = UserRepository(session), SessionRepository(session)
    passwords = PasswordService()
    auth = AuthUseCase(users, sessions, passwords, TokenService(), settings.session_ttl_hours)
    return AdminAccountsUseCase(auth=auth, users=users, sessions=sessions, passwords=passwords)


def utf8_console() -> None:
    """Console Windows mặc định cp1252, không in được tiếng Việt."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
