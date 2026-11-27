from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from app.api.deps import get_email_service
from app.main import app
from app.models import EmailChallenge
from tests.conftest import TEST_OTP, FakeEmail, new_password
from tests.test_auth import API, COOKIE, PW, login, make_admin, register

PASSWORD = f"{API}/auth/password"


async def forgot(client, email="hs01@example.com"):
    return await client.post(f"{PASSWORD}/forgot", json={"email": email})


async def verify(client, otp=TEST_OTP, email="hs01@example.com"):
    return await client.post(f"{PASSWORD}/verify-otp", json={"email": email, "otp": otp})


async def reset(client, token, password):
    return await client.post(f"{PASSWORD}/reset", json={"reset_token": token, "password": password})


def use_mail():
    mail = FakeEmail()
    app.dependency_overrides[get_email_service] = lambda: mail
    return mail


async def test_full_reset_changes_password_and_revokes_sessions(client):
    assert (await register(client)).status_code == 201
    old_cookie = client.cookies[COOKIE]
    mail = use_mail()

    response = await forgot(client, " HS01@Example.com ")
    assert response.status_code == 204 and response.headers["cache-control"] == "no-store"
    assert len(mail.outbox) == 1 and mail.outbox[0]["to"] == "hs01@example.com"
    assert "Đặt lại mật khẩu" in mail.outbox[0]["subject"] and TEST_OTP in mail.outbox[0]["text"]

    verified = await verify(client)
    assert verified.status_code == 200
    token = verified.json()["reset_token"]
    assert (await verify(client)).json()["code"] == "OTP_EXPIRED"

    new_pw = new_password()
    assert (await reset(client, token, "short")).status_code == 422
    assert (await reset(client, token, new_pw)).status_code == 204
    assert (await reset(client, token, new_password())).json()["code"] == "RESET_TOKEN_INVALID"

    client.cookies.clear()
    assert (await login(client)).status_code == 401
    assert (await login(client, password=new_pw)).status_code == 200
    client.cookies.clear()
    stale = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {old_cookie}"})
    assert stale.json()["code"] == "SESSION_REVOKED"


async def test_unknown_admin_and_known_emails_look_the_same(client, db):
    await register(client)
    await make_admin(db)
    mail = use_mail()

    for email in ("hs01@example.com", "nobody@example.com", "admin@example.com"):
        assert (await forgot(client, email)).status_code == 204
        assert (await forgot(client, email)).json()["code"] == "OTP_RESEND_LIMIT"
        assert (await verify(client, "000000", email)).json()["code"] == "OTP_INVALID"
    assert [m["to"] for m in mail.outbox] == ["hs01@example.com"]
    # Mã không được gửi tới email lạ nên đoán đúng vẫn không cấp reset_token.
    assert (await verify(client, TEST_OTP, "nobody@example.com")).json()["code"] == "OTP_INVALID"
    assert (await verify(client, TEST_OTP, "never-asked@example.com")).json()["code"] == "OTP_EXPIRED"


async def test_attempt_limit_and_expiry(client, db):
    await register(client)
    await forgot(client)
    for _ in range(4):
        assert (await verify(client, "000000")).json()["code"] == "OTP_INVALID"
    assert (await verify(client, "000000")).status_code == 429
    assert (await verify(client)).json()["code"] == "TOO_MANY_ATTEMPTS"

    async with db() as session:
        earlier = datetime.now(UTC) - timedelta(minutes=6)
        await session.execute(update(EmailChallenge).values(expires_at=earlier, sent_at=earlier, attempts=0))
        await session.commit()
    assert (await verify(client)).json()["code"] == "OTP_EXPIRED"
    assert (await forgot(client)).status_code == 204
    token = (await verify(client)).json()["reset_token"]

    async with db() as session:
        await session.execute(update(EmailChallenge).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        await session.commit()
    assert (await reset(client, token, new_password())).json()["code"] == "RESET_TOKEN_INVALID"
    assert (await login(client, password=PW)).status_code == 200
