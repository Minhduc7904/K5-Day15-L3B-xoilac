from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class DuplicateEmailError(Exception):
    """Vi phạm unique index trên lower(email)."""


class UserRepository:
    """Chỉ truy cập bảng users. Không chứa luật nghiệp vụ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(func.lower(User.email) == email.lower()))
        return result.scalar_one_or_none()

    async def add(self, email: str, password_hash: str, role: str, display_name: str | None = None) -> User:
        user = User(email=email, password_hash=password_hash, role=role, display_name=display_name)
        self._session.add(user)
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self._session.rollback()
            raise DuplicateEmailError from e
        await self._session.refresh(user)
        return user

    async def set_last_login(self, user: User, at: datetime) -> None:
        user.last_login_at = at
        await self._session.commit()
        await self._session.refresh(user)
