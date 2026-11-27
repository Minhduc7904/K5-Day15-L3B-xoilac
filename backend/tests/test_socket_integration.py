"""Test tích hợp socket (#20): uvicorn thật trên cổng tạm + socketio.AsyncClient.

Kiểm trọn luồng: xin ticket → nối → vào đúng room → ticket dùng lại bị từ chối → đăng xuất thì client nhận
session:revoked và bị ngắt. Server chạy trong thread riêng (event loop riêng), DB là SQLite dạng file với NullPool
để không dùng chung kết nối giữa hai event loop.
"""
import asyncio
import socket
import threading
import time

import httpx
import pytest
import socketio
import uvicorn
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_presence_registry
from app.api.socket.server import sio
from app.core.config import get_settings
from app.core.database import get_session
from app.main import app, asgi_app
from app.models import Base
from tests.conftest import TEST_SETTINGS, new_password

SOCKET_PATH = "/api/socket.io"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_server(tmp_path):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'socket.db').as_posix()}"

    async def _init():
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_init())
    engine = create_async_engine(url, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _session():
        async with maker() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(asgi_app, host="127.0.0.1", port=port, log_level="warning", lifespan="off"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "uvicorn không khởi động"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)
    app.dependency_overrides.clear()


async def _register(http: httpx.AsyncClient, email: str, password: str) -> str:
    r = await http.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    http.cookies.clear()  # gọi bằng Bearer; cookie còn lại trong jar sẽ thắng Bearer
    return r.cookies["examind_session"]


async def _login(http: httpx.AsyncClient, email: str, password: str) -> str:
    r = await http.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    http.cookies.clear()
    return r.cookies["examind_session"]


async def _ticket(http: httpx.AsyncClient, token: str) -> str:
    r = await http.post("/api/v1/auth/socket-ticket", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    return r.json()["ticket"]


class Conn:
    """Một kết nối client, ghi lại session:revoked và lỗi từ chối kết nối."""

    def __init__(self) -> None:
        self.client = socketio.AsyncClient(reconnection=False)
        self.revoked: list = []
        self.refused: list = []
        self.client.on("session:revoked", lambda data: self.revoked.append(data))
        self.client.on("connect_error", lambda data: self.refused.append(data))

    async def open(self, base: str, ticket: str | None) -> bool:
        try:
            await self.client.connect(
                base,
                socketio_path=SOCKET_PATH,
                transports=["websocket"],
                auth={"ticket": ticket} if ticket else None,
                wait_timeout=5,
            )
            return True
        except socketio.exceptions.ConnectionError:
            return False


async def _wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.05)
    return predicate()


async def test_ticket_connect_rooms_reuse_and_logout(live_server):
    presence = get_presence_registry()
    async with httpx.AsyncClient(base_url=live_server) as http:
        token = await _register(http, "hs01@example.com", new_password())
        ticket = await _ticket(http, token)

        conn = Conn()
        assert await conn.open(live_server, ticket)
        rooms = set(sio.rooms(conn.client.get_sid()))
        assert "role:student" in rooms and len({r for r in rooms if r.startswith("user:")}) == 1
        assert "role:admin" not in rooms
        assert await presence.count_online_students() == (1, 1)

        reused = Conn()
        assert not await reused.open(live_server, ticket)  # ticket dùng lần hai
        assert reused.refused == [{"message": "Ticket socket không hợp lệ, đã dùng hoặc đã hết hạn", "data": {"code": "TICKET_INVALID"}}]
        missing = Conn()
        assert not await missing.open(live_server, None)
        assert missing.refused[0]["data"] == {"code": "TICKET_MISSING"}
        assert await presence.count_online_students() == (1, 1)

        # Đăng xuất: client nhận session:revoked rồi bị ngắt; thống kê về 0.
        r = await http.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 204
        assert await _wait_for(lambda: conn.revoked == [{"reason": "logout"}])
        assert await _wait_for(lambda: not conn.client.connected)
        assert await presence.count_online_students() == (0, 0)


async def test_logout_kicks_only_that_session(live_server):
    """Cùng một học sinh, hai phiên (hai thiết bị). Đăng xuất phiên 1 chỉ ngắt socket của phiên 1."""
    password = new_password()
    async with httpx.AsyncClient(base_url=live_server) as http:
        token_1 = await _register(http, "hs02@example.com", password)
        token_2 = await _login(http, "hs02@example.com", password)
        one, two = Conn(), Conn()
        assert await one.open(live_server, await _ticket(http, token_1))
        assert await two.open(live_server, await _ticket(http, token_2))
        assert await get_presence_registry().count_online_students() == (1, 2)

        await http.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token_1}"})
        assert await _wait_for(lambda: not one.client.connected)
        assert one.revoked == [{"reason": "logout"}]
        await asyncio.sleep(0.3)
        assert two.client.connected and two.revoked == []
        assert await get_presence_registry().count_online_students() == (1, 1)
        await two.client.disconnect()
