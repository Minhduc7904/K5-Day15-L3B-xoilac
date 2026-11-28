from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from sqlalchemy import select, update

from app.api.realtime import RealtimeServer
from app.main import app
from app.models import UserSession
from app.service.socket_tickets import SocketTickets
from tests.test_auth import API, login, register

TICKET = f"{API}/auth/socket-ticket"


def test_ticket_expires_at_30_seconds_and_can_only_be_consumed_once():
    elapsed = 0.0
    tickets = SocketTickets(lambda: elapsed)
    taken = tickets.issue(1)
    assert tickets.consume(taken) == 1
    assert tickets.consume(taken) is None
    expired = tickets.issue(2)
    elapsed = 30.0
    assert tickets.consume(expired) is None


async def test_session_handshake_and_scoped_logout(client, db, monkeypatch):
    realtime = RealtimeServer([], lambda: db)
    server = realtime.server
    monkeypatch.setattr(server, "enter_room", AsyncMock())
    monkeypatch.setattr(server, "emit", AsyncMock())
    monkeypatch.setattr(server, "disconnect", AsyncMock())
    monkeypatch.setitem(app.state._state, "realtime", realtime)

    assert (await client.post(TICKET)).status_code == 401
    user_id = (await register(client)).json()["user_id"]
    assert not await realtime.connect("bad", {}, {})
    ticket = (await client.post(TICKET)).json()["ticket"]
    assert await realtime.connect("tab-1", {}, {"ticket": ticket})
    assert not await realtime.connect("replay", {}, {"ticket": ticket})
    ticket = (await client.post(TICKET)).json()["ticket"]
    assert await realtime.connect("tab-2", {}, {"ticket": ticket})
    assert realtime.presence.users("student") == {user_id}
    assert realtime.presence.for_user(user_id) == ["tab-1", "tab-2"]
    assert {call.args[1] for call in server.enter_room.await_args_list} == {"role:student", f"user:{user_id}"}

    # A second login opens another session for the same student.
    assert (await login(client)).status_code == 200
    assert await realtime.connect("device-2", {}, {"ticket": (await client.post(TICKET)).json()["ticket"]})
    outstanding = (await client.post(TICKET)).json()["ticket"]
    assert (await client.post(f"{API}/auth/logout")).status_code == 204
    # #20: đăng xuất gửi kèm lý do để frontend báo đúng thông báo.
    server.emit.assert_awaited_once_with("session:revoked", {"reason": "logout"}, to="device-2")
    assert not await realtime.connect("revoked", {}, {"ticket": outstanding})
    assert realtime.presence.for_user(user_id) == ["tab-1", "tab-2"]

    await realtime.revoke_user(user_id)
    assert not realtime.presence.users("student")


async def test_expired_session_is_refused_even_with_unexpired_ticket(client, db, monkeypatch):
    realtime = RealtimeServer([], lambda: db)
    monkeypatch.setitem(app.state._state, "realtime", realtime)
    await register(client)
    ticket = (await client.post(TICKET)).json()["ticket"]
    async with db.begin() as session:
        session_id = await session.scalar(select(UserSession.session_id))
        await session.execute(update(UserSession).where(UserSession.session_id == session_id).values(
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        ))
    assert not await realtime.connect("expired", {}, {"ticket": ticket})
