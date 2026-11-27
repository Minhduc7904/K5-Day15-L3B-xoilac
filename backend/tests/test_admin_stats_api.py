"""API GET /api/v1/admin/stats/online-students (#20), đọc từ PresenceRegistry giả lập bằng bản trong bộ nhớ."""
from datetime import datetime

import pytest

from app.api.deps import get_presence_registry
from app.main import app
from app.service.presence_service import InMemoryPresenceRegistry
from tests.conftest import new_password
from tests.test_auth import API, COOKIE, make_admin, register

STATS = f"{API}/admin/stats/online-students"


@pytest.fixture
def presence(client):
    registry = InMemoryPresenceRegistry()
    app.dependency_overrides[get_presence_registry] = lambda: registry
    return registry


async def _bearer(client, email, password) -> dict:
    r = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = client.cookies[COOKIE]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_h(client, db):
    pw = new_password()
    await make_admin(db, "admin@example.com", pw)
    return await _bearer(client, "admin@example.com", pw)


async def test_guest_401_student_403(client, presence):
    assert (await client.get(STATS)).json()["code"] == "SESSION_MISSING"
    await register(client)
    r = await client.get(STATS)  # cookie học sinh
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE"


async def test_counts_two_tabs_as_one_student(client, presence, admin_h):
    r = await client.get(STATS, headers=admin_h)
    assert r.status_code == 200
    body = r.json()
    assert (body["online_students"], body["connections"]) == (0, 0)
    assert set(body) == {"online_students", "connections", "as_of"}  # không include thì không có users
    assert body["as_of"].endswith("Z")
    datetime.fromisoformat(body["as_of"].replace("Z", "+00:00"))

    await presence.connect("a1", 11, "student", 1)
    await presence.connect("a2", 11, "student", 1)  # hai tab học sinh A
    await presence.connect("b1", 12, "student", 2)
    await presence.connect("adm", 99, "admin", 9)  # admin không tính
    body = (await client.get(STATS, headers=admin_h)).json()
    assert (body["online_students"], body["connections"]) == (2, 3)

    await presence.disconnect("a1")
    await presence.disconnect("a2")
    body = (await client.get(STATS, headers=admin_h)).json()
    assert (body["online_students"], body["connections"]) == (1, 1)


async def test_include_users_with_names_and_paging(client, presence, admin_h):
    a = (await register(client, email="a@example.com", display_name="Học sinh A")).json()
    b = (await register(client, email="b@example.com")).json()
    client.cookies.clear()
    await presence.connect("a1", a["user_id"], "student", 1)
    await presence.connect("a2", a["user_id"], "student", 1)
    await presence.connect("b1", b["user_id"], "student", 2)

    body = (await client.get(STATS, params={"include": "users"}, headers=admin_h)).json()
    assert body["page"] == 1 and body["page_size"] == 20
    assert body["users"] == [
        {"user_id": a["user_id"], "display_name": "Học sinh A", "email": "a@example.com", "connections": 2},
        {"user_id": b["user_id"], "display_name": None, "email": "b@example.com", "connections": 1},
    ]
    page2 = (await client.get(STATS, params={"include": "users", "page": 2, "page_size": 1}, headers=admin_h)).json()
    assert [u["user_id"] for u in page2["users"]] == [b["user_id"]]
    assert page2["online_students"] == 2  # tổng không đổi theo trang
    assert (await client.get(STATS, params={"include": "khac"}, headers=admin_h)).status_code == 422
