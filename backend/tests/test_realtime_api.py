"""API realtime (#20): POST /auth/socket-ticket và việc đăng xuất ngắt socket của đúng phiên (notifier giả)."""
from sqlalchemy import select

from app.api.deps import get_socket_ticket_service
from app.models import UserSession
from tests.test_auth import API, COOKIE, register
from tests.test_user_management_api import FakeNotifier, notifier  # noqa: F401  (fixture)


async def test_socket_ticket_requires_session(client):
    r = await client.post(f"{API}/auth/socket-ticket")
    assert r.status_code == 401 and r.json()["code"] == "SESSION_MISSING"


async def test_socket_ticket_bound_to_current_session(client, db):
    await register(client)
    r = await client.post(f"{API}/auth/socket-ticket")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"ticket", "expires_in"} and body["expires_in"] == 30
    assert r.headers["cache-control"] == "no-store"
    async with db() as s:
        session_id = (await s.execute(select(UserSession.session_id))).scalar_one()
    claim = get_socket_ticket_service().redeem(body["ticket"])
    assert claim is not None and claim.session_id == session_id


async def test_socket_ticket_works_with_bearer(client):
    await register(client)
    token = client.cookies[COOKIE]
    client.cookies.clear()
    r = await client.post(f"{API}/auth/socket-ticket", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


async def test_logout_kicks_only_that_session(client, db, notifier):  # noqa: F811
    await register(client)  # phiên 1 (cookie)
    async with db() as s:
        first = (await s.execute(select(UserSession.session_id))).scalar_one()
    r = await client.post(f"{API}/auth/logout")
    assert r.status_code == 204
    assert notifier.kicked_sessions == [(first, "logout")]
    assert notifier.kicked_users == []


async def test_logout_without_session_kicks_nothing(client, notifier):  # noqa: F811
    assert (await client.post(f"{API}/auth/logout")).status_code == 204
    assert notifier.kicked_sessions == []
