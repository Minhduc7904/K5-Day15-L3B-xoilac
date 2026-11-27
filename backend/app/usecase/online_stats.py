"""Thống kê học sinh online cho admin (#20). Đọc từ PresenceRegistry; không biết HTTP hay socket.

Online = học sinh có ít nhất một kết nối socket sống. Nhiều tab tính một học sinh, `connections` cộng đủ số kết nối.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.repositories.user_repository import UserRepository
from app.service.presence_service import PresenceRegistry


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
        students, connections = await self._presence.count_online_students()
        as_of = self._now()
        if not include_users:
            return OnlineStats(online_students=students, connections=connections, as_of=as_of)

        online, _ = await self._presence.list_online_students(offset=(page - 1) * page_size, limit=page_size)
        accounts = {u.user_id: u for u in await self._users.get_many([o.user_id for o in online])}
        listed = [
            OnlineStudent(o.user_id, accounts[o.user_id].display_name, accounts[o.user_id].email, o.connections)
            for o in online
            if o.user_id in accounts
        ]
        return OnlineStats(
            online_students=students,
            connections=connections,
            as_of=as_of,
            users=listed,
            page=page,
            page_size=page_size,
        )
