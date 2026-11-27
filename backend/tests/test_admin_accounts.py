"""Test phần B: admin tạo và quản lý admin khác (/api/v1/admin/accounts).

SQLite không có khoá dòng (FOR UPDATE bị bỏ qua), nên ca hai admin khoá lẫn nhau CÙNG LÚC được kiểm
thủ công trên PostgreSQL (xem docs/api/admin-accounts-api.md). Ở đây kiểm luật LAST_ADMIN khi gọi tuần tự.
"""
import pytest
from sqlalchemy import func, select

from app.models import User, UserSession
from tests.test_auth import API, COOKIE, make_admin, register

ACC = f"{API}/admin/accounts"
# Mật khẩu chỉ dùng trong test.
PW_A = "admin-a-test-pw"
PW_B = "admin-b-test-pw"


async def token(client, email, password) -> str:
    """Đăng nhập, lấy token rồi xoá cookie: mỗi người dùng gọi bằng Bearer riêng."""
    r = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    t = client.cookies[COOKIE]
    client.cookies.clear()
    return t


def bearer(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture
async def admin_a(client, db):
    user = await make_admin(db, "a@example.com", PW_A)
    return user, await token(client, "a@example.com", PW_A)


async def create_b(client, ta, **over):
    body = {"email": "b@example.com", "password": PW_B, "display_name": "Admin B", "current_password": PW_A, **over}
    return await client.post(ACC, json=body, headers=bearer(ta))


async def set_status(client, t, user_id, status, current_password):
    return await client.patch(
        f"{ACC}/{user_id}/status", json={"status": status, "current_password": current_password}, headers=bearer(t)
    )


async def count_users(db) -> int:
    async with db() as s:
        return (await s.execute(select(func.count()).select_from(User))).scalar_one()


# ---- Tạo admin -----------------------------------------------------------------


async def test_admin_creates_admin(client, db, admin_a):
    a, ta = admin_a
    r = await create_b(client, ta)
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"user_id", "email", "display_name", "status", "created_at", "created_by", "last_login_at"}
    assert body["email"] == "b@example.com" and body["status"] == "active"
    assert body["created_by"] == a.user_id
    assert body["last_login_at"] is None

    # Admin mới đăng nhập được và dùng được API quản lý admin.
    tb = await token(client, "b@example.com", PW_B)
    listed = await client.get(ACC, headers=bearer(tb))
    assert listed.status_code == 200
    rows = {u["email"]: u for u in listed.json()}
    assert set(rows) == {"a@example.com", "b@example.com"}
    assert rows["a@example.com"]["created_by"] is None
    assert rows["b@example.com"]["created_by"] == a.user_id
    assert rows["b@example.com"]["last_login_at"] is not None


async def test_create_wrong_current_password(client, db, admin_a):
    _, ta = admin_a
    r = await create_b(client, ta, current_password="sai-mat-khau")
    assert r.status_code == 401
    assert r.json() == {"detail": "Mật khẩu xác nhận không đúng", "code": "REAUTH_FAILED"}
    assert await count_users(db) == 1
    # Sai mật khẩu xác nhận không làm mất phiên.
    assert (await client.get(f"{API}/auth/me", headers=bearer(ta))).status_code == 200


async def test_create_duplicate_admin_email(client, admin_a):
    _, ta = admin_a
    assert (await create_b(client, ta)).status_code == 201
    r = await create_b(client, ta, email="B@Example.com")
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_TAKEN"


async def test_create_with_student_email_does_not_promote(client, db, admin_a):
    _, ta = admin_a
    await register(client, email="hs01@example.com")
    client.cookies.clear()
    r = await create_b(client, ta, email="hs01@example.com")
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_TAKEN"
    async with db() as s:
        role = (await s.execute(select(User.role).where(User.email == "hs01@example.com"))).scalar_one()
    assert role == "student"


@pytest.mark.parametrize(
    "over",
    [{"password": "12345"}, {"password": "x" * 129}, {"email": "khong-phai-email"}, {"current_password": ""}],
)
async def test_create_validation(client, admin_a, over):
    _, ta = admin_a
    assert (await create_b(client, ta, **over)).status_code == 422


# ---- Quyền -----------------------------------------------------------------------


async def test_student_forbidden_and_guest_unauthorized(client, db, admin_a):
    a, _ = admin_a
    await register(client, email="hs01@example.com")
    ts = client.cookies[COOKIE]
    client.cookies.clear()

    calls = [
        ("GET", ACC, None),
        ("POST", ACC, {"email": "x@example.com", "password": "123456", "current_password": "hs01"}),
        ("PATCH", f"{ACC}/{a.user_id}/status", {"status": "disabled", "current_password": "hs01"}),
    ]
    for method, url, body in calls:
        r = await client.request(method, url, json=body, headers=bearer(ts))
        assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE", (method, r.text)
        r = await client.request(method, url, json=body)
        assert r.status_code == 401 and r.json()["code"] == "SESSION_MISSING", (method, r.text)
    assert await count_users(db) == 2


async def test_register_still_only_creates_student(client, admin_a):
    r = await register(client, email="moi@example.com", role="admin")
    assert r.status_code == 201 and r.json()["role"] == "student"


# ---- Khoá / mở khoá -------------------------------------------------------------


async def test_cannot_disable_self(client, admin_a):
    a, ta = admin_a
    await create_b(client, ta)
    r = await set_status(client, ta, a.user_id, "disabled", PW_A)
    assert r.status_code == 409
    assert r.json() == {"detail": "Không thể đổi trạng thái tài khoản của chính mình", "code": "CANNOT_MODIFY_SELF"}


async def test_cannot_disable_last_active_admin(client, admin_a):
    a, ta = admin_a
    r = await set_status(client, ta, a.user_id, "disabled", PW_A)
    assert r.status_code == 409
    assert r.json() == {"detail": "Không thể khóa admin đang hoạt động cuối cùng", "code": "LAST_ADMIN"}
    assert (await client.get(f"{API}/auth/me", headers=bearer(ta))).status_code == 200


async def test_disable_other_admin_revokes_sessions_then_enable(client, db, admin_a):
    _, ta = admin_a
    b_id = (await create_b(client, ta)).json()["user_id"]
    tb1 = await token(client, "b@example.com", PW_B)
    tb2 = await token(client, "b@example.com", PW_B)

    # Sai mật khẩu xác nhận: không đổi gì.
    r = await set_status(client, ta, b_id, "disabled", "sai-mat-khau")
    assert r.status_code == 401 and r.json()["code"] == "REAUTH_FAILED"
    assert (await client.get(f"{API}/auth/me", headers=bearer(tb1))).status_code == 200

    r = await set_status(client, ta, b_id, "disabled", PW_A)
    assert r.status_code == 200 and r.json()["status"] == "disabled"

    # Mọi phiên của B bị thu hồi ngay: mã của #8.
    for t in (tb1, tb2):
        me = await client.get(f"{API}/auth/me", headers=bearer(t))
        assert me.status_code == 401 and me.json()["code"] == "SESSION_REVOKED"
    async with db() as s:
        open_sessions = (
            await s.execute(
                select(func.count()).select_from(UserSession).where(
                    UserSession.user_id == b_id, UserSession.revoked_at.is_(None)
                )
            )
        ).scalar_one()
    assert open_sessions == 0
    login = await client.post(f"{API}/auth/login", json={"email": "b@example.com", "password": PW_B})
    assert login.status_code == 403 and login.json()["code"] == "ACCOUNT_DISABLED"

    # Mở khoá: đăng nhập lại được; phiên cũ vẫn bị thu hồi.
    r = await set_status(client, ta, b_id, "active", PW_A)
    assert r.status_code == 200 and r.json()["status"] == "active"
    tb3 = await token(client, "b@example.com", PW_B)
    assert (await client.get(f"{API}/auth/me", headers=bearer(tb3))).status_code == 200
    assert (await client.get(f"{API}/auth/me", headers=bearer(tb1))).json()["code"] == "SESSION_REVOKED"


async def test_disabled_admin_cannot_be_counted_as_remaining(client, admin_a):
    """A khoá B, rồi A là admin active duy nhất: A tự khoá → LAST_ADMIN. Khoá lại B (đã khoá) → không đổi."""
    a, ta = admin_a
    b_id = (await create_b(client, ta)).json()["user_id"]
    assert (await set_status(client, ta, b_id, "disabled", PW_A)).status_code == 200
    assert (await set_status(client, ta, a.user_id, "disabled", PW_A)).json()["code"] == "LAST_ADMIN"
    again = await set_status(client, ta, b_id, "disabled", PW_A)
    assert again.status_code == 200 and again.json()["status"] == "disabled"


async def test_status_not_found_for_missing_or_student(client, admin_a):
    _, ta = admin_a
    student = (await register(client, email="hs01@example.com")).json()
    client.cookies.clear()
    for user_id in (9999, student["user_id"]):
        r = await set_status(client, ta, user_id, "disabled", PW_A)
        assert r.status_code == 404 and r.json()["code"] == "ACCOUNT_NOT_FOUND"


async def test_status_validation(client, admin_a):
    a, ta = admin_a
    r = await client.patch(f"{ACC}/{a.user_id}/status", json={"status": "banned", "current_password": PW_A}, headers=bearer(ta))
    assert r.status_code == 422
    r = await client.patch(f"{ACC}/{a.user_id}/status", json={"status": "disabled"}, headers=bearer(ta))
    assert r.status_code == 422


async def test_list_never_exposes_secrets(client, admin_a):
    _, ta = admin_a
    text = (await client.get(ACC, headers=bearer(ta))).text
    assert "password" not in text and "argon2" not in text and "token" not in text
