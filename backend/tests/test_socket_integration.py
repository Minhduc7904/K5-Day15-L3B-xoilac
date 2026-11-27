"""Test tích hợp socket (#20): uvicorn thật trên cổng tạm + socketio.AsyncClient.

Kiểm trọn luồng: xin ticket → nối → vào đúng room → ticket dùng lại bị từ chối → đăng xuất thì client nhận
session:revoked và bị ngắt. Server chạy trong thread riêng (event loop riêng), DB là SQLite dạng file với NullPool
để không dùng chung kết nối giữa hai event loop.
"""
import asyncio
import socket
import threading
import time
from types import SimpleNamespace

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
    yield SimpleNamespace(base=f"http://127.0.0.1:{port}", db_url=url)
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
    base = live_server.base
    async with httpx.AsyncClient(base_url=base) as http:
        token = await _register(http, "hs01@example.com", new_password())
        ticket = await _ticket(http, token)

        conn = Conn()
        assert await conn.open(base, ticket)
        rooms = set(sio.rooms(conn.client.get_sid()))
        assert "role:student" in rooms and len({r for r in rooms if r.startswith("user:")}) == 1
        assert "role:admin" not in rooms
        assert await presence.count_online_students() == (1, 1)

        reused = Conn()
        assert not await reused.open(base, ticket)  # ticket dùng lần hai
        assert reused.refused == [{"message": "Ticket socket không hợp lệ, đã dùng hoặc đã hết hạn", "data": {"code": "TICKET_INVALID"}}]
        missing = Conn()
        assert not await missing.open(base, None)
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
    base = live_server.base
    async with httpx.AsyncClient(base_url=base) as http:
        token_1 = await _register(http, "hs02@example.com", password)
        token_2 = await _login(http, "hs02@example.com", password)
        one, two = Conn(), Conn()
        assert await one.open(base, await _ticket(http, token_1))
        assert await two.open(base, await _ticket(http, token_2))
        assert await get_presence_registry().count_online_students() == (1, 2)

        await http.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token_1}"})
        assert await _wait_for(lambda: not one.client.connected)
        assert one.revoked == [{"reason": "logout"}]
        await asyncio.sleep(0.3)
        assert two.client.connected and two.revoked == []
        assert await get_presence_registry().count_online_students() == (1, 1)
        await two.client.disconnect()


async def _make_admin(db_url: str, email: str, password: str) -> None:
    """Tạo admin thẳng trong DB của server (engine riêng, NullPool)."""
    from app.repositories.session_repository import SessionRepository
    from app.repositories.user_repository import UserRepository
    from app.service.password_service import PasswordService
    from app.service.token_service import TokenService
    from app.usecase.auth import AuthUseCase

    engine = create_async_engine(db_url, poolclass=NullPool)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        await AuthUseCase(UserRepository(s), SessionRepository(s), PasswordService(), TokenService(), 168).create_user(
            email, password, "admin"
        )
    await engine.dispose()


async def test_two_tabs_stats_and_disable_kicks(live_server):
    """Kịch bản nghiệm thu: A mở 2 tab, B mở 1 → 2 học sinh, 3 kết nối; đóng tab của A → 1, 1;
    admin khoá B → B nhận session:revoked {reason: disabled}, bị ngắt, thống kê về 0."""
    base, admin_pw = live_server.base, new_password()
    await _make_admin(live_server.db_url, "admin@example.com", admin_pw)
    async with httpx.AsyncClient(base_url=base) as http:
        token_a = await _register(http, "a@example.com", new_password())
        token_b = await _register(http, "b@example.com", new_password())
        admin = {"Authorization": f"Bearer {await _login(http, 'admin@example.com', admin_pw)}"}

        async def stats():
            r = await http.get("/api/v1/admin/stats/online-students", headers=admin)
            assert r.status_code == 200, r.text
            return r.json()["online_students"], r.json()["connections"]

        a1, a2, b1 = Conn(), Conn(), Conn()
        assert await a1.open(base, await _ticket(http, token_a))
        assert await a2.open(base, await _ticket(http, token_a))
        assert await b1.open(base, await _ticket(http, token_b))
        assert await stats() == (2, 3)

        await a1.client.disconnect()
        await a2.client.disconnect()
        assert await _wait_for(lambda: True, 0.3)
        assert await stats() == (1, 1)

        me_b = await http.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})
        r = await http.patch(f"/api/v1/admin/users/{me_b.json()['user_id']}", json={"status": "disabled"}, headers=admin)
        assert r.status_code == 200
        assert await _wait_for(lambda: b1.revoked == [{"reason": "disabled"}], 3)
        assert await _wait_for(lambda: not b1.client.connected, 3)
        assert await stats() == (0, 0)
