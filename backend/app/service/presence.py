from dataclasses import dataclass


@dataclass(frozen=True)
class SocketConnection:
    user_id: int
    session_id: int
    role: str


class PresenceRegistry:
    """Tracks multiple connections for each user without counting users twice."""

    def __init__(self) -> None:
        self._connections: dict[str, SocketConnection] = {}

    def add(self, sid: str, connection: SocketConnection) -> None:
        self._connections[sid] = connection

    def remove(self, sid: str) -> None:
        self._connections.pop(sid, None)

    def get(self, sid: str) -> SocketConnection | None:
        return self._connections.get(sid)

    def for_session(self, session_id: int) -> list[str]:
        return [sid for sid, record in self._connections.items() if record.session_id == session_id]

    def for_user(self, user_id: int) -> list[str]:
        return [sid for sid, record in self._connections.items() if record.user_id == user_id]

    def users(self, role: str) -> set[int]:
        return {record.user_id for record in self._connections.values() if record.role == role}

    def connections_by_user(self, role: str) -> dict[int, int]:
        """user_id → số kết nối đang mở, chỉ tính vai trò `role`. Nhiều tab của một người cộng dồn (#20)."""
        counts: dict[int, int] = {}
        for record in self._connections.values():
            if record.role == role:
                counts[record.user_id] = counts.get(record.user_id, 0) + 1
        return counts
