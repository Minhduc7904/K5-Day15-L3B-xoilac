"""Kết nối socket theo vai trò (#20). Không import socketio hay fastapi.

- issue_ticket: phiên HTTP hợp lệ xin ticket một lần (30 s).
- admit: handler connect đổi ticket thành người dùng, kiểm lại phiên gắn với ticket (chưa thu hồi, chưa hết hạn,
  user còn active), ghi nhận vào PresenceRegistry và trả các room cần vào.
- leave: handler disconnect gỡ kết nối khỏi PresenceRegistry.
Room trả về ở dạng khoá trừu tượng ("role", vai trò) / ("user", user_id); tên room do api/socket/rooms.py sinh.
"""
from dataclasses import dataclass
from typing import Literal

from app.service.presence_service import PresenceRegistry
from app.service.socket_ticket_service import SocketTicketService
from app.usecase.auth import AuthError, AuthUseCase, CurrentUser

RoomKey = tuple[Literal["role", "user"], str | int]


class TicketMissing(AuthError):
    code = "TICKET_MISSING"
    message = "Thiếu ticket socket"


class TicketInvalid(AuthError):
    code = "TICKET_INVALID"
    message = "Ticket socket không hợp lệ, đã dùng hoặc đã hết hạn"


@dataclass(frozen=True)
class Admission:
    user_id: int
    role: str
    session_id: int
    rooms: tuple[RoomKey, ...]


def rooms_for(role: str, user_id: int) -> tuple[RoomKey, ...]:
    """Mỗi kết nối vào room của vai trò (phát tin, đếm online) và room riêng của người đó (gửi riêng)."""
    return (("role", role), ("user", user_id))


class RealtimeUseCase:
    def __init__(self, tickets: SocketTicketService, presence: PresenceRegistry, auth: AuthUseCase) -> None:
        self._tickets = tickets
        self._presence = presence
        self._auth = auth

    def issue_ticket(self, current: CurrentUser) -> tuple[str, int]:
        """Trả (ticket, số giây còn hiệu lực). Gắn với user và phiên đang dùng."""
        return self._tickets.issue(current.user_id, current.session_id), self._tickets.ttl_seconds

    async def admit(self, ticket: object, sid: str) -> Admission:
        """Từ chối bằng AuthError: TICKET_MISSING, TICKET_INVALID, hoặc lỗi phiên của #8
        (SESSION_REVOKED, SESSION_EXPIRED, SESSION_INVALID, ACCOUNT_DISABLED)."""
        if not isinstance(ticket, str) or not ticket:
            raise TicketMissing()
        claim = self._tickets.redeem(ticket)
        if claim is None:
            raise TicketInvalid()
        current = await self._auth.get_current_user_by_session(claim.session_id)
        if current.user_id != claim.user_id:
            raise TicketInvalid()
        await self._presence.connect(sid, current.user_id, current.role, current.session_id)
        return Admission(
            user_id=current.user_id,
            role=current.role,
            session_id=current.session_id,
            rooms=rooms_for(current.role, current.user_id),
        )

    async def leave(self, sid: str) -> None:
        await self._presence.disconnect(sid)
