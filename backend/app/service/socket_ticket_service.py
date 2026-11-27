"""Ticket một lần để nối socket (#20).

Trình duyệt ở origin khác backend nên cookie phiên không đi theo handshake WebSocket. Client xin ticket qua
HTTP (có phiên), rồi gửi ticket trong `auth` khi nối. Ticket:
- ngẫu nhiên (secrets.token_urlsafe), sống `ttl_seconds` (mặc định 30), dùng đúng một lần;
- gắn với user_id VÀ session_id của phiên đã xin, để đăng xuất phiên đó ngắt đúng các socket của nó;
- chỉ lưu SHA-256 trong bộ nhớ của tiến trình (backend chạy một worker; nhiều worker cần Redis).
"""
import hashlib
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class TicketClaim:
    user_id: int
    session_id: int


class SocketTicketService:
    def __init__(self, ttl_seconds: int = 30, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._store: dict[str, tuple[TicketClaim, float]] = {}

    @property
    def ttl_seconds(self) -> int:
        return self._ttl

    def issue(self, user_id: int, session_id: int) -> str:
        self._purge_expired()
        ticket = secrets.token_urlsafe(32)
        self._store[self._hash(ticket)] = (TicketClaim(user_id, session_id), self._clock() + self._ttl)
        return ticket

    def redeem(self, ticket: str) -> TicketClaim | None:
        """Đổi ticket lấy claim và xoá ngay (dùng một lần). Lạ, đã dùng hoặc hết hạn → None."""
        entry = self._store.pop(self._hash(ticket), None)
        if entry is None:
            return None
        claim, expires_at = entry
        return claim if self._clock() < expires_at else None

    def _purge_expired(self) -> None:
        now = self._clock()
        for key in [k for k, (_, exp) in self._store.items() if exp <= now]:
            del self._store[key]

    @staticmethod
    def _hash(ticket: str) -> str:
        return hashlib.sha256(ticket.encode("utf-8")).hexdigest()
