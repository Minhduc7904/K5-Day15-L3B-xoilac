"""Test issue #8: đăng ký, đăng nhập, phiên, phân quyền. Chạy bằng SQLite trong bộ nhớ (conftest.py)."""
import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from app.api.deps import get_password_service
from app.models import User, UserSession
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.service.token_service import TokenService
from app.usecase.auth import AuthUseCase
from tests.conftest import TEST_OTP, new_password

API = "/api/v1"
COOKIE = "examind_session"
ADMIN_COOKIE = "examind_admin_session"
# Sinh lúc chạy, không viết cứng (tests/conftest.py).
PW = new_password()


async def register(client, email="hs01@example.com", password=PW, **extra):
    started = await client.post(f"{API}/auth/register", json={"email": email, "password": password, **extra})
    if started.status_code != 202:
        return started
    return await client.post(
        f"{API}/auth/otp/verify",
        json={"purpose": "registration", "challenge": started.json()["challenge"], "otp": TEST_OTP},
    )


async def login(client, email="hs01@example.com", password=PW):
    return await client.post(f"{API}/auth/login", json={"email": email, "password": password})


async def make_admin(db, email="admin@example.com", password=PW):
    async with db() as s:
        uc = AuthUseCase(UserRepository(s), SessionRepository(s), get_password_service(), TokenService(), 168)
        return await uc.create_user(email, password, "admin")


def set_cookie_header(r) -> str:
    return "; ".join(r.headers.get_list("set-cookie"))


# ---- Đăng ký -----------------------------------------------------------------


async def test_register_creates_student_and_sets_cookie(client, db):
    r = await register(client, display_name="  Học sinh 01 ")
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"user_id", "email", "role", "status", "display_name", "created_at"}
    assert body["role"] == "student" and body["status"] == "active"
    assert body["display_name"] == "Học sinh 01"

    header = set_cookie_header(r)
    assert f"{COOKIE}=" in header
    assert "HttpOnly" in header and "Path=/" in header and "Max-Age=604800" in header
    assert "samesite=lax" in header.lower()
    assert "Secure" not in header  # COOKIE_SECURE=false trong test
    assert r.headers["cache-control"] == "no-store"

    # CSDL chỉ lưu SHA-256 của token.
    token = client.cookies[COOKIE]
    async with db() as s:
        stored = (await s.execute(select(UserSession.token_hash))).scalar_one()
    assert stored == hashlib.sha256(token.encode()).hexdigest() != token


async def test_register_ignores_role_admin(client, db):
    r = await register(client, role="admin")
    assert r.status_code == 201
    assert r.json()["role"] == "student"
    async with db() as s:
        roles = (await s.execute(select(User.role))).scalars().all()
    assert roles == ["student"]


async def test_register_normalizes_email_and_rejects_duplicate_case_insensitive(client):
    r = await register(client, email="  HS01@Example.COM ")
    assert r.status_code == 201
    assert r.json()["email"] == "hs01@example.com"

    dup = await register(client, email="hs01@EXAMPLE.com")
    assert dup.status_code == 409
    assert dup.json() == {"detail": "Email này đã được đăng ký", "code": "EMAIL_TAKEN"}


@pytest.mark.parametrize(
    ("password", "expected"),
    [("x" * 7, 422), ("x" * 8, 201), ("x" * 128, 201), ("x" * 129, 422)],
)
async def test_register_password_length(client, password, expected):
    r = await register(client, password=password)
    assert r.status_code == expected


@pytest.mark.parametrize("email", ["khong-phai-email", "a@", "@example.com", ""])
async def test_register_invalid_email(client, email):
    assert (await register(client, email=email)).status_code == 422


async def test_register_missing_fields(client):
    assert (await client.post(f"{API}/auth/register", json={"email": "a@example.com"})).status_code == 422
    assert (await client.post(f"{API}/auth/register", json={"password": PW})).status_code == 422


# ---- Đăng nhập ---------------------------------------------------------------


async def test_login_success_sets_cookie_and_last_login(client, db):
    await register(client)
    client.cookies.clear()
    r = await login(client, email=" HS01@example.com ")
    assert r.status_code == 200
    assert r.json()["email"] == "hs01@example.com"
    assert COOKIE in client.cookies
    async with db() as s:
        assert (await s.execute(select(User.last_login_at))).scalar_one() is not None


@pytest.mark.parametrize("length", [6, 7])
async def test_legacy_short_password_still_logs_in(client, db, length):
    """Luật 8 ký tự chỉ áp cho mật khẩu mới. Tài khoản đặt mật khẩu 6–7 ký tự trước đó vẫn đăng nhập được."""
    legacy = new_password()[:length]
    async with db() as s:
        await UserRepository(s).add("cu@example.com", get_password_service().hash_sync(legacy), "student")
    r = await login(client, email="cu@example.com", password=legacy)
    assert r.status_code == 200 and r.json()["email"] == "cu@example.com"


async def test_login_wrong_email_and_wrong_password_same_message(client, make_password):
    await register(client)
    client.cookies.clear()
    wrong_pw = await login(client, password=make_password())
    no_user = await login(client, email="khongco@example.com")
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json() == {
        "detail": "Email hoặc mật khẩu không đúng",
        "code": "INVALID_CREDENTIALS",
    }
    assert COOKIE not in client.cookies


async def test_login_unknown_email_still_verifies_hash(client):
    """Email không tồn tại vẫn chạy verify argon2 (verify_dummy) để thời gian phản hồi không lộ email."""
    calls = []
    real = get_password_service()

    class Spy(type(real)):
        async def verify_dummy(self, password):
            calls.append(1)
            await real.verify_dummy(password)

    from app.main import app

    app.dependency_overrides[get_password_service] = Spy
    r = await login(client, email="khongco@example.com")
    assert r.status_code == 401
    assert calls == [1]


async def test_login_disabled_account(client, db, make_password):
    await register(client)
    client.cookies.clear()
    async with db() as s:
        await s.execute(update(User).values(status="disabled"))
        await s.commit()
    r = await login(client)
    assert r.status_code == 403
    assert r.json()["code"] == "ACCOUNT_DISABLED"
    # Sai mật khẩu thì vẫn 401 như mọi tài khoản: không lộ việc tài khoản bị khóa.
    assert (await login(client, password=make_password())).status_code == 401


# ---- Phiên: /me, logout, hết hạn, thu hồi, khóa -----------------------------


async def test_me_with_cookie(client):
    created = (await register(client)).json()
    r = await client.get(f"{API}/auth/me")
    assert r.status_code == 200
    assert r.json() == created


async def test_me_with_bearer(client):
    await register(client)
    token = client.cookies[COOKIE]
    client.cookies.clear()
    r = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "hs01@example.com"


async def test_me_without_session(client):
    r = await client.get(f"{API}/auth/me")
    assert r.status_code == 401
    assert r.json() == {"detail": "Chưa đăng nhập", "code": "SESSION_MISSING"}
    assert r.headers["www-authenticate"] == "Bearer"


async def test_me_with_unknown_token(client):
    r = await client.get(f"{API}/auth/me", headers={"Authorization": "Bearer khong-ton-tai"})
    assert r.status_code == 401
    assert r.json()["code"] == "SESSION_INVALID"


async def test_cookie_wins_over_bearer(client):
    await register(client, email="b@example.com")
    bearer = client.cookies[COOKIE]
    client.cookies.clear()
    await register(client, email="a@example.com")  # cookie của a
    r = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {bearer}"})
    assert r.json()["email"] == "a@example.com"


async def test_me_updates_last_used_at(client, db):
    await register(client)
    async with db() as s:
        assert (await s.execute(select(UserSession.last_used_at))).scalar_one() is None
    await client.get(f"{API}/auth/me")
    async with db() as s:
        assert (await s.execute(select(UserSession.last_used_at))).scalar_one() is not None


async def test_logout_revokes_session_immediately(client, db):
    await register(client)
    token = client.cookies[COOKIE]

    r = await client.post(f"{API}/auth/logout")
    assert r.status_code == 204
    assert f'{COOKIE}=""' in set_cookie_header(r) and "Max-Age=0" in set_cookie_header(r)
    assert COOKIE not in client.cookies

    # Cookie đã xoá: thiếu phiên.
    me = await client.get(f"{API}/auth/me")
    assert me.status_code == 401 and me.json()["code"] == "SESSION_MISSING"
    # Dùng lại token cũ: phiên đã thu hồi.
    again = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert again.status_code == 401 and again.json()["code"] == "SESSION_REVOKED"
    async with db() as s:
        assert (await s.execute(select(UserSession.revoked_at))).scalar_one() is not None


async def test_logout_without_session_is_204(client):
    r = await client.post(f"{API}/auth/logout")
    assert r.status_code == 204
    assert "Max-Age=0" in set_cookie_header(r)


async def test_logout_is_idempotent_for_dead_sessions(client, db):
    """Phiên đã thu hồi, token lạ, phiên hết hạn: đều 204 và xoá cookie (frontend không phải xử lý 401)."""
    await register(client)
    token = client.cookies[COOKIE]
    assert (await client.post(f"{API}/auth/logout")).status_code == 204
    # Gọi lại bằng token đã thu hồi.
    again = await client.post(f"{API}/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert again.status_code == 204 and "Max-Age=0" in set_cookie_header(again)
    # Token không khớp phiên nào.
    bogus = await client.post(f"{API}/auth/logout", headers={"Authorization": "Bearer khong-ton-tai"})
    assert bogus.status_code == 204


async def test_logout_expired_session_is_204_and_revokes(client, db):
    await register(client)
    async with db() as s:
        await s.execute(update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        await s.commit()
    r = await client.post(f"{API}/auth/logout")
    assert r.status_code == 204 and "Max-Age=0" in set_cookie_header(r)
    async with db() as s:
        assert (await s.execute(select(UserSession.revoked_at))).scalar_one() is not None


async def test_logout_only_revokes_current_session(client):
    await register(client)
    first = client.cookies[COOKIE]
    client.cookies.clear()
    await login(client)  # phiên thứ hai, đang trong cookie
    await client.post(f"{API}/auth/logout")
    r = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {first}"})
    assert r.status_code == 200


async def test_expired_session_rejected_and_cookie_cleared(client, db):
    await register(client)
    async with db() as s:
        await s.execute(update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        await s.commit()
    r = await client.get(f"{API}/auth/me")
    assert r.status_code == 401
    assert r.json() == {"detail": "Phiên đã hết hạn, hãy đăng nhập lại", "code": "SESSION_EXPIRED"}
    assert "Max-Age=0" in set_cookie_header(r)


async def test_session_of_disabled_account_rejected(client, db):
    await register(client)
    async with db() as s:
        await s.execute(update(User).values(status="disabled"))
        await s.commit()
    r = await client.get(f"{API}/auth/me")
    assert r.status_code == 403
    assert r.json()["code"] == "ACCOUNT_DISABLED"


# ---- Phân quyền ----------------------------------------------------------------


async def test_admin_ping_requires_session(client):
    r = await client.get(f"{API}/admin/ping")
    assert r.status_code == 401 and r.json()["code"] == "SESSION_MISSING"


async def test_student_cannot_call_admin(client):
    await register(client)
    r = await client.get(f"{API}/admin/ping")
    assert r.status_code == 403
    assert r.json() == {"detail": "Tài khoản không có quyền dùng chức năng này", "code": "FORBIDDEN_ROLE"}


async def test_admin_can_call_admin(client, db):
    admin = await make_admin(db)
    r = await login(client, email="admin@example.com")
    assert r.status_code == 200 and r.json()["role"] == "admin"
    ping = await client.get(f"{API}/admin/ping")
    assert ping.status_code == 200
    assert ping.json() == {"status": "ok", "user_id": admin.user_id, "role": "admin"}


async def test_admin_email_cannot_be_registered_publicly(client, db):
    await make_admin(db)
    r = await register(client, email="ADMIN@example.com")
    assert r.status_code == 409
    async with db() as s:
        assert (await s.execute(select(func.count()).select_from(User))).scalar_one() == 1
