"""API /api/v1/admin/users (#20) với RealtimeNotifier giả (không cần socket thật)."""
import pytest
from sqlalchemy import func, select

from app.api.deps import get_realtime_notifier
from app.main import app
from app.models import User, UserSession
from app.repositories.user_repository import UserRepository
from tests.conftest import new_password
from tests.test_auth import API, COOKIE, make_admin, register

USERS = f"{API}/admin/users"


class FakeNotifier:
    def __init__(self) -> None:
        self.kicked_users: list[tuple[int, str]] = []
        self.kicked_sessions: list[tuple[int, str]] = []

    async def kick_user(self, user_id: int, reason: str) -> None:
        self.kicked_users.append((user_id, reason))

    async def kick_session(self, session_id: int, reason: str) -> None:
        self.kicked_sessions.append((session_id, reason))


@pytest.fixture
def notifier(client):
    fake = FakeNotifier()
    app.dependency_overrides[get_realtime_notifier] = lambda: fake
    return fake


async def bearer_for(client, email, password) -> dict:
    r = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = client.cookies[COOKIE]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def people(client, db, notifier):
    """Admin gốc, một admin thường, một học sinh; mỗi người một header Bearer."""
    pw = {k: new_password() for k in ("root", "admin", "student")}
    root = await make_admin(db, "root@example.com", pw["root"])
    async with db() as s:
        repo = UserRepository(s)
        await repo.set_root(await repo.get(root.user_id))
    admin = await make_admin(db, "admin@example.com", pw["admin"])
    student = (await register(client, email="hs01@example.com", password=pw["student"])).json()
    client.cookies.clear()
    return {
        "root": {"id": root.user_id, "h": await bearer_for(client, "root@example.com", pw["root"]), "pw": pw["root"]},
        "admin": {"id": admin.user_id, "h": await bearer_for(client, "admin@example.com", pw["admin"]), "pw": pw["admin"]},
        "student": {"id": student["user_id"], "h": await bearer_for(client, "hs01@example.com", pw["student"]), "pw": pw["student"]},
    }


async def open_sessions(db, user_id) -> int:
    async with db() as s:
        q = select(func.count()).select_from(UserSession).where(
            UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
        )
        return (await s.execute(q)).scalar_one()


# ---- Quyền truy cập -----------------------------------------------------------------


async def test_guest_401_student_403(client, people):
    s = people["student"]
    for method, url, body in [
        ("GET", USERS, None),
        ("GET", f"{USERS}/{s['id']}", None),
        ("POST", USERS, {"email": "x@example.com", "password": new_password()}),
        ("PATCH", f"{USERS}/{s['id']}", {"display_name": "X"}),
        ("POST", f"{USERS}/{s['id']}/reset-password", {"password": new_password()}),
    ]:
        r = await client.request(method, url, json=body)
        assert r.status_code == 401 and r.json()["code"] == "SESSION_MISSING", (method, url)
        r = await client.request(method, url, json=body, headers=s["h"])
        assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE", (method, url)


# ---- Danh sách và chi tiết ---------------------------------------------------------------


async def test_list_filter_search_and_paginate(client, people):
    h = people["admin"]["h"]
    for i in range(3):
        await client.post(USERS, json={"email": f"lop10_{i}@example.com", "password": new_password(), "display_name": f"Học sinh {i}"}, headers=h)

    body = (await client.get(USERS, headers=h)).json()
    assert body["total"] == 6 and body["page"] == 1 and body["page_size"] == 20
    assert all("password_hash" not in u for u in body["items"])
    assert [u["is_root"] for u in body["items"] if u["email"] == "root@example.com"] == [True]

    admins = (await client.get(USERS, params={"role": "admin"}, headers=h)).json()
    assert {u["email"] for u in admins["items"]} == {"root@example.com", "admin@example.com"}

    found = (await client.get(USERS, params={"q": "LOP10"}, headers=h)).json()
    assert found["total"] == 3
    by_name = (await client.get(USERS, params={"q": "học sinh 1"}, headers=h)).json()
    assert [u["email"] for u in by_name["items"]] == ["lop10_1@example.com"]
    # Ký tự đại diện của LIKE được hiểu là chữ thường.
    assert (await client.get(USERS, params={"q": "%"}, headers=h)).json()["total"] == 0

    page2 = (await client.get(USERS, params={"page": 2, "page_size": 4}, headers=h)).json()
    assert page2["total"] == 6 and len(page2["items"]) == 2

    disabled = (await client.get(USERS, params={"status": "disabled"}, headers=h)).json()
    assert disabled["total"] == 0
    assert (await client.get(USERS, params={"page_size": 101}, headers=h)).status_code == 422


async def test_get_detail_and_404(client, people):
    h = people["admin"]["h"]
    r = await client.get(f"{USERS}/{people['root']['id']}", headers=h)  # admin thường xem được admin
    assert r.status_code == 200 and r.json()["is_root"] is True
    r = await client.get(f"{USERS}/9999", headers=h)
    assert r.status_code == 404 and r.json() == {"detail": "Không có tài khoản này", "code": "USER_NOT_FOUND"}


# ---- Tạo -------------------------------------------------------------------------------


async def test_create(client, db, people):
    a, root = people["admin"], people["root"]
    r = await client.post(USERS, json={"email": " Moi@Example.com ", "password": new_password()}, headers=a["h"])
    assert r.status_code == 201
    assert (r.json()["role"], r.json()["email"], r.json()["created_by"], r.json()["is_root"]) == (
        "student", "moi@example.com", a["id"], False
    )

    r = await client.post(USERS, json={"email": "ad2@example.com", "password": new_password(), "role": "admin"}, headers=a["h"])
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE"

    r = await client.post(USERS, json={"email": "ad2@example.com", "password": new_password(), "role": "admin"}, headers=root["h"])
    assert r.status_code == 201 and r.json()["role"] == "admin" and r.json()["created_by"] == root["id"]

    r = await client.post(USERS, json={"email": "MOI@example.com", "password": new_password()}, headers=a["h"])
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_TAKEN"

    assert (await client.post(USERS, json={"email": "x@example.com", "password": "x" * 7}, headers=a["h"])).status_code == 422
    r = await client.post(USERS, json={"email": "x@example.com", "password": new_password(), "is_root": True}, headers=root["h"])
    assert r.status_code == 422  # không ai đặt is_root qua API
    async with db() as s:
        assert (await s.execute(select(func.count()).select_from(User).where(User.is_root.is_(True)))).scalar_one() == 1


# ---- Sửa và khoá --------------------------------------------------------------------------


async def test_update_student_fields_and_email_conflict(client, people, notifier):
    a, st = people["admin"], people["student"]
    r = await client.patch(f"{USERS}/{st['id']}", json={"display_name": "  Tên mới ", "email": "HS01.MOI@example.com"}, headers=a["h"])
    assert r.status_code == 200
    assert (r.json()["display_name"], r.json()["email"]) == ("Tên mới", "hs01.moi@example.com")
    assert notifier.kicked_users == []  # đổi tên/email không ngắt phiên

    r = await client.patch(f"{USERS}/{st['id']}", json={"email": "Admin@Example.com"}, headers=a["h"])
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_TAKEN"
    assert (await client.patch(f"{USERS}/{st['id']}", json={"is_root": True}, headers=a["h"])).status_code == 422
    assert (await client.patch(f"{USERS}/9999", json={"display_name": "X"}, headers=a["h"])).status_code == 404


async def test_disable_student_revokes_sessions_and_kicks(client, db, people, notifier):
    a, st = people["admin"], people["student"]
    assert await open_sessions(db, st["id"]) == 2  # phiên đăng ký + phiên đăng nhập

    r = await client.patch(f"{USERS}/{st['id']}", json={"status": "disabled"}, headers=a["h"])
    assert r.status_code == 200 and r.json()["status"] == "disabled"
    assert await open_sessions(db, st["id"]) == 0
    assert notifier.kicked_users == [(st["id"], "disabled")]

    me = await client.get(f"{API}/auth/me", headers=st["h"])
    assert me.status_code == 401 and me.json()["code"] == "SESSION_REVOKED"
    login = await client.post(f"{API}/auth/login", json={"email": "hs01@example.com", "password": st["pw"]})
    assert login.status_code == 403 and login.json()["code"] == "ACCOUNT_DISABLED"

    # Mở khoá: đăng nhập lại được, không kick thêm.
    r = await client.patch(f"{USERS}/{st['id']}", json={"status": "active"}, headers=a["h"])
    assert r.status_code == 200 and notifier.kicked_users == [(st["id"], "disabled")]
    assert (await client.post(f"{API}/auth/login", json={"email": "hs01@example.com", "password": st["pw"]})).status_code == 200


async def test_plain_admin_cannot_touch_admin_accounts(client, people, notifier):
    a, root = people["admin"], people["root"]
    other = (await client.post(USERS, json={"email": "ad2@example.com", "password": new_password(), "role": "admin"}, headers=root["h"])).json()
    for body in ({"display_name": "X"}, {"status": "disabled"}, {"role": "student"}):
        r = await client.patch(f"{USERS}/{other['user_id']}", json=body, headers=a["h"])
        assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE", body
    r = await client.post(f"{USERS}/{other['user_id']}/reset-password", json={"password": new_password()}, headers=a["h"])
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE"
    r = await client.patch(f"{USERS}/{people['student']['id']}", json={"role": "admin"}, headers=a["h"])
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE"  # không nâng học sinh
    assert notifier.kicked_users == []


async def test_root_manages_admins_and_demotion_kicks(client, db, people, notifier):
    root, a = people["root"], people["admin"]
    r = await client.patch(f"{USERS}/{a['id']}", json={"role": "student"}, headers=root["h"])
    assert r.status_code == 200 and r.json()["role"] == "student"
    assert notifier.kicked_users == [(a["id"], "role_changed")]
    assert await open_sessions(db, a["id"]) == 0
    # Nâng lại thành admin: không ngắt phiên.
    r = await client.patch(f"{USERS}/{a['id']}", json={"role": "admin"}, headers=root["h"])
    assert r.status_code == 200 and notifier.kicked_users == [(a["id"], "role_changed")]


async def test_root_is_protected(client, people, notifier):
    root, a = people["root"], people["admin"]
    for body in ({"status": "disabled"}, {"role": "student"}, {"email": "x@example.com"}):
        r = await client.patch(f"{USERS}/{root['id']}", json=body, headers=a["h"])
        assert r.status_code == 403 and r.json()["code"] == "CANNOT_MODIFY_ROOT", body
        r = await client.patch(f"{USERS}/{root['id']}", json=body, headers=root["h"])
        assert r.status_code == 403 and r.json()["code"] == "CANNOT_MODIFY_ROOT", body
    r = await client.post(f"{USERS}/{root['id']}/reset-password", json={"password": new_password()}, headers=root["h"])
    assert r.status_code == 403 and r.json()["code"] == "CANNOT_MODIFY_ROOT"
    r = await client.patch(f"{USERS}/{root['id']}", json={"display_name": "Admin gốc"}, headers=root["h"])
    assert r.status_code == 200 and r.json()["display_name"] == "Admin gốc"
    r = await client.patch(f"{USERS}/{root['id']}", json={"display_name": "X"}, headers=a["h"])
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE"
    assert notifier.kicked_users == []


async def test_cannot_disable_or_demote_self(client, people):
    root, a = people["root"], people["admin"]
    # Admin thường tự khoá / tự hạ: CANNOT_MODIFY_SELF.
    for body in ({"status": "disabled"}, {"role": "student"}):
        r = await client.patch(f"{USERS}/{a['id']}", json=body, headers=a["h"])
        assert r.status_code == 403 and r.json()["code"] == "CANNOT_MODIFY_SELF", body


# ---- Đặt lại mật khẩu ------------------------------------------------------------------


async def test_reset_password(client, db, people, notifier):
    a, st = people["admin"], people["student"]
    new_pw = new_password()
    r = await client.post(f"{USERS}/{st['id']}/reset-password", json={"password": new_pw}, headers=a["h"])
    assert r.status_code == 204
    assert notifier.kicked_users == [(st["id"], "password_reset")]
    assert await open_sessions(db, st["id"]) == 0
    assert (await client.get(f"{API}/auth/me", headers=st["h"])).json()["code"] == "SESSION_REVOKED"
    old = await client.post(f"{API}/auth/login", json={"email": "hs01@example.com", "password": st["pw"]})
    assert old.status_code == 401
    assert (await client.post(f"{API}/auth/login", json={"email": "hs01@example.com", "password": new_pw})).status_code == 200
    client.cookies.clear()  # cookie học sinh vừa đăng nhập sẽ thắng Bearer của admin

    assert (await client.post(f"{USERS}/{st['id']}/reset-password", json={"password": "x" * 7}, headers=a["h"])).status_code == 422
    assert (await client.post(f"{USERS}/9999/reset-password", json={"password": new_password()}, headers=a["h"])).status_code == 404


async def test_register_still_only_creates_student(client, people):
    r = await register(client, email="tudangky@example.com", role="admin")
    assert r.status_code == 201 and r.json()["role"] == "student"
