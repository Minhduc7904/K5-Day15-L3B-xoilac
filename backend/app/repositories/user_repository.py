from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.study_time import study_date
from app.models.user import ROLE_STUDENT, User
from app.repositories.credits import CreditRepository


class DuplicateEmailError(Exception):
    """Vi phạm unique index trên lower(email)."""


class DuplicateRootError(Exception):
    """Vi phạm unique index một phần uq_users_single_root (đã có admin gốc khác)."""


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
    async def get_many(self, user_ids: Sequence[int]) -> Sequence[User]:
        if not user_ids:
            return []
        result = await self._session.execute(select(User).where(User.user_id.in_(list(user_ids))))
        return result.scalars().all()


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

    async def get_root(self) -> User | None:
        result = await self._session.execute(select(User).where(User.is_root.is_(True)))
        return result.scalar_one_or_none()

    async def set_root(self, user: User) -> None:
        user.is_root = True
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self._session.rollback()
            raise DuplicateRootError from e
        await self._session.refresh(user)

    async def search(
        self, role: str | None, status: str | None, q: str | None, offset: int, limit: int
    ) -> tuple[Sequence[User], int]:
        """Lọc theo vai trò, trạng thái và chuỗi q (khớp một phần email hoặc display_name, không phân biệt hoa
        thường). Trả (trang kết quả theo user_id tăng dần, tổng số dòng khớp)."""
        conditions = []
        if role:
            conditions.append(User.role == role)
        if status:
            conditions.append(User.status == status)
        if q:
            # Thoát ký tự đại diện của LIKE để q là chuỗi thường (vd "50%" không khớp mọi thứ).
            escaped = q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            conditions.append(
                or_(
                    func.lower(User.email).like(pattern, escape="\\"),
                    func.lower(func.coalesce(User.display_name, "")).like(pattern, escape="\\"),
                )
            )
        total = (await self._session.execute(select(func.count()).select_from(User).where(*conditions))).scalar_one()
        rows = await self._session.execute(
            select(User).where(*conditions).order_by(User.user_id).offset(offset).limit(limit)
        )
        return rows.scalars().all(), total

    async def update(self, user: User, values: Mapping[str, Any]) -> None:
        """Ghi các trường đã được usecase kiểm. Commit ngay; trùng email (đua nhau) → DuplicateEmailError."""
        for key, value in values.items():
            setattr(user, key, value)
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self._session.rollback()
            raise DuplicateEmailError from e
        await self._session.refresh(user)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
