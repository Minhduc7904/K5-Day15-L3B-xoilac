from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.study_time import study_date
from app.models.user import ROLE_STUDENT, User
from app.repositories.credits import CreditRepository


class DuplicateEmailError(Exception):
    """Vi phạm unique index trên lower(email)."""


class UserRepository:
    """Lưu tài khoản và khởi tạo ví học sinh trong cùng giao dịch."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str, *, lock: bool = False) -> User | None:
        query = select(User).where(func.lower(User.email) == email.lower())
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return (await self._session.execute(query)).scalar_one_or_none()

    async def get_by_google_subject(self, subject: str, *, lock: bool = False) -> User | None:
        query = select(User).where(User.google_subject == subject)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return (await self._session.execute(query)).scalar_one_or_none()

    async def add(
        self,
        email: str,
        password_hash: str | None,
        role: str,
        display_name: str | None = None,
        created_by: int | None = None,
        *,
        verified_at: datetime | None = None,
        google_subject: str | None = None,
        commit: bool = True,
    ) -> User:
        user = User(
            email=email, password_hash=password_hash, role=role, display_name=display_name, created_by=created_by,
            email_verified_at=verified_at, google_subject=google_subject,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(user)
                await self._session.flush()
        except IntegrityError as error:
            raise DuplicateEmailError from error
        if role == ROLE_STUDENT:
            await self._session.refresh(user, attribute_names=["created_at"])
            created_at = user.created_at if user.created_at.tzinfo else user.created_at.replace(tzinfo=UTC)
            await CreditRepository(self._session).open_account(user.user_id, study_date(created_at))
        if commit:
            await self._session.commit()
        await self._session.refresh(user)
        return user

    async def link_google(self, user: User, subject: str, at: datetime) -> None:
        try:
            async with self._session.begin_nested():
                user.google_subject = subject
                if user.email_verified_at is None:
                    user.email_verified_at = at
                    user.password_hash = None
                await self._session.flush()
        except IntegrityError as error:
            raise DuplicateEmailError from error

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
