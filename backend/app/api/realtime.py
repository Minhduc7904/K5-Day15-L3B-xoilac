import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime

import socketio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.service.presence import PresenceRegistry, SocketConnection
from app.service.socket_tickets import SocketTickets
from app.usecase.realtime import RealtimeAuthorization

log = logging.getLogger(__name__)
SOCKET_PATH = "/api/socket.io"
SESSION_REVOKED = "session:revoked"


def rooms_for(connection: SocketConnection) -> tuple[str, str]:
    return f"role:{connection.role}", f"user:{connection.user_id}"


class RealtimeServer:
    def __init__(
        self, allowed_origins: list[str], get_sessions: Callable[[], async_sessionmaker[AsyncSession]],
    ) -> None:
        self.server = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=allowed_origins or None)
        self.tickets = SocketTickets()
        self.presence = PresenceRegistry()
        self._get_sessions = get_sessions
        self._expiry: dict[str, asyncio.TimerHandle] = {}
        self.server.on("connect", self.connect)
        self.server.on("disconnect", self.disconnect)

    async def connect(self, sid: str, environ: dict, auth: object) -> bool:
        ticket = auth.get("ticket") if isinstance(auth, dict) else None
        session_id = self.tickets.consume(ticket) if isinstance(ticket, str) else None
        if session_id is None:
            return False
        authorization = RealtimeAuthorization(self._get_sessions())
        authorized = await authorization.authorize(session_id)
        if authorized is None:
            return False

        self.presence.add(sid, authorized.connection)
        try:
            for room in rooms_for(authorized.connection):
                await self.server.enter_room(sid, room)
            # Close the race with a revocation committed while the handshake was joining rooms.
            if await authorization.authorize(session_id) is None:
                self.presence.remove(sid)
                return False
        except Exception:
            self.presence.remove(sid)
            log.error("Socket handshake failed")
            return False
        delay = max(0, (authorized.expires_at - datetime.now(UTC)).total_seconds())
        self._expiry[sid] = asyncio.get_running_loop().call_later(
            delay, lambda: asyncio.create_task(self._revoke([sid]))
        )
        return True

    async def disconnect(self, sid: str, reason: str | None = None) -> None:
        self.presence.remove(sid)
        timer = self._expiry.pop(sid, None)
        if timer is not None:
            timer.cancel()

    async def revoke_session(self, session_id: int) -> None:
        await self._revoke(self.presence.for_session(session_id))

    async def revoke_user(self, user_id: int) -> None:
        await self._revoke(self.presence.for_user(user_id))

    async def _revoke(self, sids: list[str]) -> None:
        for sid in sids:
            try:
                try:
                    await self.server.emit(SESSION_REVOKED, to=sid)
                finally:
                    await self.server.disconnect(sid)
            except Exception:
                log.error("Socket revocation failed")
            finally:
                await self.disconnect(sid)


class RealtimeMiddleware(socketio.ASGIApp):
    def __init__(self, app, realtime: RealtimeServer) -> None:
        super().__init__(realtime.server, app, socketio_path=SOCKET_PATH)
