from collections.abc import Sequence
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

    async def add(
        self,
        email: str,
        password_hash: str,
        role: str,
        display_name: str | None = None,
        created_by: int | None = None,
    ) -> User:
        user = User(
            email=email, password_hash=password_hash, role=role, display_name=display_name, created_by=created_by
        )
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

    async def list_by_role(self, role: str) -> Sequence[User]:
        result = await self._session.execute(select(User).where(User.role == role).order_by(User.user_id))
        return result.scalars().all()

    # Các hàm dưới KHÔNG commit: usecase gom nhiều thay đổi vào một transaction rồi gọi commit()/rollback().

    async def lock_by_role(self, role: str) -> Sequence[User]:
        """SELECT ... FOR UPDATE mọi tài khoản của vai trò, theo thứ tự user_id để hai transaction
        khoá cùng thứ tự (tránh deadlock). populate_existing: đọc lại status mới nhất sau khi chờ khoá,
        không dùng bản cũ trong identity map. SQLite (test) bỏ qua FOR UPDATE."""
        result = await self._session.execute(
            select(User)
            .where(User.role == role)
            .order_by(User.user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalars().all()

    async def set_status(self, user: User, status: str) -> None:
        user.status = status
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
