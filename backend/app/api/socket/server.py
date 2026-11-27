"""Server Socket.IO (#20): tạo `sio` một lần và đăng ký handler mỏng, chỉ gọi RealtimeUseCase.

Gắn vào FastAPI ở app/main.py tại /api/socket.io (khớp location của nginx).
cors_allowed_origins lấy từ CORS_ORIGINS. Danh sách rỗng thì truyền None (chỉ cùng origin), KHÔNG truyền []:
với python-engineio, [] tắt hẳn việc kiểm origin.
Ping/pong: ping_interval 25 s, ping_timeout 20 s (giá trị mặc định của Socket.IO, ghi rõ để thống kê online dựa vào).
"""
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

import socketio

from app.api.socket.rooms import room_name
from app.core.config import get_settings
from app.usecase.auth import AuthError
from app.usecase.realtime import RealtimeUseCase

PING_INTERVAL = 25
PING_TIMEOUT = 20

RealtimeScope = Callable[[], AbstractAsyncContextManager[RealtimeUseCase]]


def create_sio() -> socketio.AsyncServer:
    return socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=get_settings().cors_origin_list or None,
        ping_interval=PING_INTERVAL,
        ping_timeout=PING_TIMEOUT,
        logger=False,
        engineio_logger=False,
    )


sio = create_sio()


def register_handlers(server: socketio.AsyncServer, realtime_scope: RealtimeScope) -> None:
    @server.event
    async def connect(sid: str, environ: dict, auth: object = None) -> None:
        ticket = auth.get("ticket") if isinstance(auth, dict) else None
        try:
            async with realtime_scope() as usecase:
                admission = await usecase.admit(ticket, sid)
        except AuthError as e:
            # Phải là lớp của python-socketio (không phải ConnectionRefusedError có sẵn của Python), nếu không
            # client chỉ nhận câu mặc định. Client nhận connect_error: {"message": ..., "data": {"code": ...}}.
            raise socketio.exceptions.ConnectionRefusedError(e.message, {"code": e.code}) from None
        for key in admission.rooms:
            await server.enter_room(sid, room_name(key))

    @server.event
    async def disconnect(sid: str, *_: object) -> None:
        async with realtime_scope() as usecase:
            await usecase.leave(sid)
