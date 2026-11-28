import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime

import socketio
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.exam_attempts import ExamAttemptRepository
from app.repositories.notifications import NotificationRepository
from app.repositories.question_bank_repository import QuestionBankRepository
from app.schemas.exam_attempt import AttemptSave
from app.schemas.notification import NotificationOut
from app.service.presence import PresenceRegistry, SocketConnection
from app.service.socket_tickets import SocketTickets
from app.usecase.exam_attempts import AttemptError, ExamAttempts
from app.usecase.realtime import RealtimeAuthorization
from app.usecase.realtime_notifier import RevokeReason

log = logging.getLogger(__name__)
SOCKET_PATH = "/api/socket.io"
SESSION_REVOKED = "session:revoked"
NOTIFICATION_NEW = "notification:new"


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
        self._attempts: dict[str, int] = {}
        self._attempt_revisions: dict[int, int] = {}
        self._attempt_watch: asyncio.Task | None = None
        self._notice_watch: asyncio.Task | None = None
        self.server.on("connect", self.connect)
        self.server.on("disconnect", self.disconnect)
        self.server.on("attempt:join", self.join_attempt)
        self.server.on("attempt:leave", self.leave_attempt)
        self.server.on("attempt:save", self.save_attempt)

    async def _student(self, sid: str) -> SocketConnection:
        record = self.presence.get(sid)
        if not record or record.role != "student":
            raise AttemptError(403, "STUDENT_REQUIRED", "Cần phiên học sinh hợp lệ.")
        authorization = RealtimeAuthorization(self._get_sessions())
        if await authorization.authorize(record.session_id) is None:
            raise AttemptError(403, "STUDENT_REQUIRED", "Cần phiên học sinh hợp lệ.")
        return record

    @staticmethod
    def _error(error: AttemptError) -> dict:
        return {"ok": False, "code": error.code, "message": str(error)}

    async def join_attempt(self, sid: str, payload: dict):
        try:
            record = await self._student(sid)
            attempt_id = payload.get("attempt_id") if isinstance(payload, dict) else None
            if type(attempt_id) is not int or not 0 < attempt_id <= 2_147_483_647:
                raise AttemptError(422, "INVALID_ATTEMPT", "Mã lượt làm không hợp lệ.")
            async with self._get_sessions()() as session:
                usecase = ExamAttempts(ExamAttemptRepository(session), QuestionBankRepository(session))
                state = await usecase.read(record.user_id, attempt_id)
            await self.leave_attempt(sid)
            await self.server.enter_room(sid, f"attempt:{attempt_id}")
            self._attempts[sid] = attempt_id
            self._attempt_revisions.setdefault(attempt_id, state["revision"])
            if self._attempt_watch is None or self._attempt_watch.done():
                self._attempt_watch = asyncio.create_task(self._watch_attempts())
            return {"ok": True, "state": jsonable_encoder(state)}
        except AttemptError as error:
            return self._error(error)

    async def leave_attempt(self, sid: str, payload=None):
        attempt_id = self._attempts.get(sid)
        if attempt_id is None or (isinstance(payload, dict) and payload.get("attempt_id") != attempt_id):
            return
        self._remove_attempt(sid)
        await self.server.leave_room(sid, f"attempt:{attempt_id}")

    def _remove_attempt(self, sid: str):
        attempt_id = self._attempts.pop(sid, None)
        if attempt_id not in self._attempts.values():
            self._attempt_revisions.pop(attempt_id, None)

    async def save_attempt(self, sid: str, payload: dict):
        try:
            record = await self._student(sid)
            attempt_id = self._attempts.get(sid)
            if attempt_id is None or not isinstance(payload, dict) or payload.get("attempt_id") != attempt_id:
                raise AttemptError(409, "ATTEMPT_ROOM_REQUIRED", "Hãy kết nối lại lượt làm bài.")
            data = AttemptSave.model_validate(payload.get("update"))
            async with self._get_sessions()() as session:
                usecase = ExamAttempts(ExamAttemptRepository(session), QuestionBankRepository(session))
                state = await usecase.save(record.user_id, attempt_id, data)
            return {"ok": True, "state": jsonable_encoder(state)}
        except ValidationError:
            return self._error(AttemptError(422, "INVALID_UPDATE", "Dữ liệu lưu không hợp lệ."))
        except AttemptError as error:
            return self._error(error)

    async def _watch_attempts(self):
        while self._attempt_revisions:
            try:
                async with self._get_sessions()() as session:
                    rows = await ExamAttemptRepository(session).revisions(list(self._attempt_revisions))
                for attempt_id, revision, reason in rows:
                    previous = self._attempt_revisions.get(attempt_id)
                    if previous is None or revision <= previous:
                        continue
                    event = "attempt:finished" if reason else "attempt:updated"
                    await self.server.emit(event, {"attempt_id": attempt_id, "revision": revision, "reason": reason},
                                           to=f"attempt:{attempt_id}")
                    if self._attempt_revisions.get(attempt_id) == previous:
                        self._attempt_revisions[attempt_id] = revision
            except Exception:
                log.exception("Could not broadcast attempt updates")
            await asyncio.sleep(1)

    def _ensure_notification_watch(self):
        if self._notice_watch is None or self._notice_watch.done():
            self._notice_watch = asyncio.create_task(self._watch_notifications())

    async def _watch_notifications(self):
        """Tiến trình API phát thông báo mới cho học sinh đang kết nối.

        Worker chạy tiến trình riêng nên ghi thông báo vào DB; ở đây đọc bản ghi mới theo id và đẩy vào `user:<id>`.
        Học sinh vắng mặt không cần phát, vì lần mở sau client tải danh sách từ API.
        """
        try:
            async with self._get_sessions()() as session:
                last = await NotificationRepository(session).latest_id()
            while self.presence.users("student"):
                try:
                    async with self._get_sessions()() as session:
                        rows = await NotificationRepository(session).after(last)
                    online = self.presence.users("student")
                    for row in rows:
                        last = row.id
                        if row.user_id in online:
                            await self.server.emit(
                                NOTIFICATION_NEW, jsonable_encoder(NotificationOut.model_validate(row)),
                                to=f"user:{row.user_id}",
                            )
                except Exception:
                    log.exception("Could not broadcast notifications")
                await asyncio.sleep(2)
        finally:
            self._notice_watch = None

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
        if authorized.connection.role == "student":
            self._ensure_notification_watch()
        delay = max(0, (authorized.expires_at - datetime.now(UTC)).total_seconds())
        self._expiry[sid] = asyncio.get_running_loop().call_later(
            delay, lambda: asyncio.create_task(self._revoke([sid], "expired"))
        )
        return True

    async def disconnect(self, sid: str, reason: str | None = None) -> None:
        self._remove_attempt(sid)
        self.presence.remove(sid)
        timer = self._expiry.pop(sid, None)
        if timer is not None:
            timer.cancel()

    async def revoke_session(self, session_id: int, reason: RevokeReason | None = None) -> None:
        await self._revoke(self.presence.for_session(session_id), reason)

    async def revoke_user(self, user_id: int, reason: RevokeReason | None = None) -> None:
        await self._revoke(self.presence.for_user(user_id), reason)

    async def _revoke(self, sids: list[str], reason: RevokeReason | None = None) -> None:
        # #20: kèm {"reason"} khi biết lý do; không có lý do thì gửi như trước (không payload).
        payload = {"reason": reason} if reason else None
        for sid in sids:
            try:
                try:
                    await self.server.emit(SESSION_REVOKED, payload, to=sid)
                finally:
                    await self.server.disconnect(sid)
            except Exception:
                log.error("Socket revocation failed")
            finally:
                await self.disconnect(sid)


class RealtimeMiddleware(socketio.ASGIApp):
    def __init__(self, app, realtime: RealtimeServer) -> None:
        super().__init__(realtime.server, app, socketio_path=SOCKET_PATH)
