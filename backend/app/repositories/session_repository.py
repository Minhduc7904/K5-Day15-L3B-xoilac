from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import UserSession
from app.models.user import User


class SessionRepository:
    """Chỉ truy cập bảng sessions. Không chứa luật nghiệp vụ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_id: int, token_hash: str, expires_at: datetime, user_agent: str | None) -> UserSession:
        row = UserSession(user_id=user_id, token_hash=token_hash, expires_at=expires_at, user_agent=user_agent)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def get_with_user(self, token_hash: str) -> tuple[UserSession, User] | None:
        result = await self._session.execute(
            select(UserSession, User)
            .join(User, User.user_id == UserSession.user_id)
            .where(UserSession.token_hash == token_hash)
        )
        row = result.first()
        return (row[0], row[1]) if row else None

    async def touch(self, row: UserSession, at: datetime) -> None:
        row.last_used_at = at
        await self._session.commit()

    async def revoke(self, row: UserSession, at: datetime) -> None:
        row.revoked_at = at
        await self._session.commit()
