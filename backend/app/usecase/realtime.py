from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.session_repository import SessionRepository
from app.service.presence import SocketConnection
from app.usecase.auth import AuthError, validate_session


@dataclass(frozen=True)
class AuthorizedConnection:
    connection: SocketConnection
    expires_at: datetime


class RealtimeAuthorization:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def authorize(self, session_id: int) -> AuthorizedConnection | None:
        async with self._sessions() as session:
            pair = await SessionRepository(session).get_by_id_with_user(session_id)
            try:
                row, user = validate_session(pair, datetime.now(UTC))
            except AuthError:
                return None
            expires_at = row.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            return AuthorizedConnection(SocketConnection(user.user_id, row.session_id, user.role), expires_at)
