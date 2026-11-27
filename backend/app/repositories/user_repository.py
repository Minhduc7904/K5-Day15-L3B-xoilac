from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class DuplicateEmailError(Exception):
    """Vi phạm unique index trên lower(email)."""


class DuplicateRootError(Exception):
    """Vi phạm unique index một phần uq_users_single_root (đã có admin gốc khác)."""


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
