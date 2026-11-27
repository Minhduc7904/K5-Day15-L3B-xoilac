"""Ai đang online qua socket (#20).

`PresenceRegistry` là Protocol: usecase chỉ biết giao diện này. Bản trong bộ nhớ dưới đây đủ cho MỘT tiến trình
backend. Chạy nhiều worker hoặc nhiều máy thì cần bản cài đặt dùng Redis (cùng giao diện, phương thức async),
kèm AsyncRedisManager cho Socket.IO.

Online = học sinh có ít nhất một kết nối sống. Kết nối "sống" do ping/pong của Socket.IO quyết định
(ping_interval 25 s, ping_timeout 20 s): client mất mạng bị server coi là ngắt sau tối đa khoảng 45 s.
"""
from dataclasses import dataclass
from typing import Protocol

from app.models.user import ROLE_STUDENT


@dataclass(frozen=True)
class Connection:
    sid: str
    user_id: int
    role: str
    session_id: int


@dataclass(frozen=True)
class OnlineUser:
    user_id: int
    connections: int


class PresenceRegistry(Protocol):
    async def connect(self, sid: str, user_id: int, role: str, session_id: int) -> None: ...
    async def disconnect(self, sid: str) -> Connection | None: ...
    async def sids_of_user(self, user_id: int) -> list[str]: ...
    async def sids_of_session(self, session_id: int) -> list[str]: ...
    async def count_online_students(self) -> tuple[int, int]:
        """(số học sinh online, tổng số kết nối của học sinh)."""
        ...

    async def list_online_students(self, offset: int, limit: int) -> tuple[list[OnlineUser], int]:
        """(trang học sinh online theo user_id tăng dần, tổng số học sinh online)."""
        ...


class InMemoryPresenceRegistry:
    """sid → Connection và user_id → tập sid. Chỉ dùng trong một tiến trình, một event loop."""

    def __init__(self) -> None:
        self._by_sid: dict[str, Connection] = {}
        self._by_user: dict[int, set[str]] = {}

    async def connect(self, sid: str, user_id: int, role: str, session_id: int) -> None:
        await self.disconnect(sid)  # sid trùng (hiếm): ghi đè sạch
        self._by_sid[sid] = Connection(sid, user_id, role, session_id)
        self._by_user.setdefault(user_id, set()).add(sid)

    async def disconnect(self, sid: str) -> Connection | None:
        conn = self._by_sid.pop(sid, None)
        if conn is not None:
            sids = self._by_user.get(conn.user_id)
            if sids is not None:
                sids.discard(sid)
                if not sids:
                    del self._by_user[conn.user_id]
        return conn

    async def sids_of_user(self, user_id: int) -> list[str]:
        return sorted(self._by_user.get(user_id, ()))

    async def sids_of_session(self, session_id: int) -> list[str]:
        return sorted(c.sid for c in self._by_sid.values() if c.session_id == session_id)

    async def count_online_students(self) -> tuple[int, int]:
        students = self._students()
        return len(students), sum(students.values())

    async def list_online_students(self, offset: int, limit: int) -> tuple[list[OnlineUser], int]:
        students = self._students()
        page = sorted(students)[offset : offset + limit]
        return [OnlineUser(uid, students[uid]) for uid in page], len(students)

    def _students(self) -> dict[int, int]:
        """user_id → số kết nối, chỉ tính kết nối có vai trò học sinh."""
        counts: dict[int, int] = {}
        for conn in self._by_sid.values():
            if conn.role == ROLE_STUDENT:
                counts[conn.user_id] = counts.get(conn.user_id, 0) + 1
        return counts
