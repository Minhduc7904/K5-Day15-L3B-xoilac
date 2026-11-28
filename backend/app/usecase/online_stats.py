"""Thống kê học sinh online cho admin (#20). Đọc từ PresenceRegistry; không biết HTTP hay socket.

Online = học sinh có ít nhất một kết nối socket sống. Nhiều tab tính một học sinh, `connections` cộng đủ số kết nối.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.models.user import ROLE_STUDENT
from app.repositories.user_repository import UserRepository
from app.service.presence import PresenceRegistry


@dataclass(frozen=True)
class OnlineStudent:
    user_id: int
    display_name: str | None
    email: str
    connections: int


@dataclass(frozen=True)
class OnlineStats:
    online_students: int
    connections: int
    as_of: datetime
    users: list[OnlineStudent] | None = None
    page: int | None = None
    page_size: int | None = None


class OnlineStatsUseCase:
    def __init__(
        self,
        presence: PresenceRegistry,
        users: UserRepository,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._presence = presence
        self._users = users
        self._now = now

    async def online_students(self, include_users: bool = False, page: int = 1, page_size: int = 20) -> OnlineStats:
        counts = self._presence.connections_by_user(ROLE_STUDENT)
        students, connections = len(counts), sum(counts.values())
        as_of = self._now()
        if not include_users:
            return OnlineStats(online_students=students, connections=connections, as_of=as_of)

        page_ids = sorted(counts)[(page - 1) * page_size : page * page_size]
        accounts = {u.user_id: u for u in await self._users.get_many(page_ids)}
        listed = [
            OnlineStudent(uid, accounts[uid].display_name, accounts[uid].email, counts[uid])
            for uid in page_ids
            if uid in accounts
        ]
        return OnlineStats(
            online_students=students,
            connections=connections,
            as_of=as_of,
            users=listed,
            page=page,
            page_size=page_size,
        )
