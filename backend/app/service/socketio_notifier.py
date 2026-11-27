"""Cài đặt RealtimeNotifier bằng python-socketio (#20)."""
import socketio

from app.service.presence_service import PresenceRegistry
from app.usecase.ports import RevokeReason

SESSION_REVOKED = "session:revoked"


class SocketIONotifier:
    """Gửi "session:revoked" {"reason": ...} tới đúng các sid rồi ngắt chúng.

    Handler disconnect sẽ gỡ sid khỏi PresenceRegistry, nên thống kê online cập nhật ngay.
    """

    def __init__(self, sio: socketio.AsyncServer, presence: PresenceRegistry) -> None:
        self._sio = sio
        self._presence = presence

    async def kick_user(self, user_id: int, reason: RevokeReason) -> None:
        await self._kick(await self._presence.sids_of_user(user_id), reason)

    async def kick_session(self, session_id: int, reason: RevokeReason) -> None:
        await self._kick(await self._presence.sids_of_session(session_id), reason)

    async def _kick(self, sids: list[str], reason: RevokeReason) -> None:
        for sid in sids:
            await self._sio.emit(SESSION_REVOKED, {"reason": reason}, to=sid)
            await self._sio.disconnect(sid)
