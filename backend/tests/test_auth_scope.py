"""Phiên admin và học sinh dùng cookie riêng, đăng nhập song song trong cùng một trình duyệt."""
from tests.test_auth import ADMIN_COOKIE, API, COOKIE, PW, login, make_admin, register

ADMIN = {"X-Auth-Scope": "admin"}
STUDENT = {"X-Auth-Scope": "student"}


async def both_sessions(client, db):
    await make_admin(db, "admin@example.com", PW)
    assert (await register(client)).status_code == 201
    assert (await login(client, email="admin@example.com")).status_code == 200


async def test_login_sets_cookie_by_role_and_keeps_the_other_session(client, db):
    await both_sessions(client, db)
    assert COOKIE in client.cookies and ADMIN_COOKIE in client.cookies

    as_admin = await client.get(f"{API}/auth/me", headers=ADMIN)
    as_student = await client.get(f"{API}/auth/me", headers=STUDENT)
    assert as_admin.json()["role"] == "admin"
    assert as_student.json()["role"] == "student"


async def test_scope_picks_cookie_and_requires_matching_session(client, db):
    await make_admin(db, "admin@example.com", PW)
    assert (await register(client)).status_code == 201
    # Chỉ có phiên học sinh: phạm vi admin không dùng được phiên đó.
    assert (await client.get(f"{API}/auth/me", headers=ADMIN)).status_code == 401
    assert (await client.get(f"{API}/auth/me", headers=STUDENT)).status_code == 200


async def test_scoped_cookie_with_wrong_role_is_rejected(client, db):
    await make_admin(db, "admin@example.com", PW)
    assert (await login(client, email="admin@example.com")).status_code == 200
    client.cookies.set(COOKIE, client.cookies[ADMIN_COOKIE])  # phiên admin nằm nhầm trong cookie học sinh
    assert (await client.get(f"{API}/auth/me", headers=STUDENT)).status_code == 401
    assert (await client.get(f"{API}/auth/me", headers=ADMIN)).status_code == 200


async def test_logout_only_ends_the_scoped_session(client, db):
    await both_sessions(client, db)
    assert (await client.post(f"{API}/auth/logout", headers=ADMIN)).status_code == 204
    assert ADMIN_COOKIE not in client.cookies and COOKIE in client.cookies
    assert (await client.get(f"{API}/auth/me", headers=ADMIN)).status_code == 401
    assert (await client.get(f"{API}/auth/me", headers=STUDENT)).status_code == 200

    assert (await client.post(f"{API}/auth/logout", headers=STUDENT)).status_code == 204
    assert COOKIE not in client.cookies
    assert (await client.get(f"{API}/auth/me", headers=STUDENT)).status_code == 401


async def test_expired_scoped_session_clears_only_that_cookie(client, db):
    await both_sessions(client, db)
    await client.post(f"{API}/auth/logout", headers=ADMIN)  # thu hồi phiên admin
    client.cookies.set(ADMIN_COOKIE, "token-da-thu-hoi")
    bad = await client.get(f"{API}/auth/me", headers=ADMIN)
    assert bad.status_code == 401
    assert (await client.get(f"{API}/auth/me", headers=STUDENT)).status_code == 200
