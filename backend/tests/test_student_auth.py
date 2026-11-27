from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import func, select, update

from app.api.deps import get_email_service, get_google_identity, get_password_service
from app.core.config import Settings
from app.main import app
from app.models import EmailChallenge, User
from app.repositories.user_repository import UserRepository
from app.service.google_identity import GoogleIdentity, GoogleIdentityError, GoogleIdentityService, browser_challenge
from app.service.token_service import TokenService
from tests.conftest import TEST_OTP, FakeEmail
from tests.test_auth import API, COOKIE, PW, login, make_admin, register

OTP = f"{API}/auth/otp"
GOOGLE = f"{API}/auth/google"


async def start_registration(client, email="hs01@example.com"):
    return await client.post(f"{API}/auth/register", json={"email": email, "password": PW})


async def verify_otp(client, challenge, otp=TEST_OTP, purpose="registration"):
    return await client.post(f"{OTP}/verify", json={"challenge": challenge, "otp": otp, "purpose": purpose})


async def resend_otp(client, challenge, purpose="registration"):
    return await client.post(f"{OTP}/resend", json={"challenge": challenge, "purpose": purpose})


async def test_registration_waits_for_otp_and_sends_branded_email(client, db):
    mail = FakeEmail()
    app.dependency_overrides[get_email_service] = lambda: mail
    response = await start_registration(client)
    assert response.status_code == 202 and COOKIE not in client.cookies
    assert response.headers["cache-control"] == "no-store"
    assert (await login(client)).status_code == 401
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email["to"] == "hs01@example.com"
    assert TEST_OTP in email["text"] and TEST_OTP in email["html"]
    assert "cid:examind-logo" in email["html"] and email["logo"].startswith(b"\x89PNG")

    challenge = response.json()["challenge"]
    assert (await verify_otp(client, challenge, "000000")).json()["code"] == "OTP_INVALID"
    verified = await verify_otp(client, challenge)
    assert verified.status_code == 201 and COOKIE in client.cookies
    assert (await verify_otp(client, challenge)).json()["code"] == "INVALID_CHALLENGE"
    async with db() as session:
        user = (await session.execute(select(User))).scalar_one()
        assert user.email_verified_at is not None
        draft = (await session.execute(select(EmailChallenge))).scalar_one()
        assert draft.payload is None and draft.otp_hash is None


async def test_otp_expiry_attempt_limit_and_resend(client, db, monkeypatch):
    pending = await start_registration(client)
    challenge = pending.json()["challenge"]
    assert (await resend_otp(client, challenge)).status_code == 429
    for _ in range(4):
        assert (await verify_otp(client, challenge, "000000")).json()["code"] == "OTP_INVALID"
    assert (await verify_otp(client, challenge, "000000")).json()["code"] == "TOO_MANY_ATTEMPTS"
    assert (await verify_otp(client, challenge)).status_code == 429

    async with db() as session:
        earlier = datetime.now(UTC) - timedelta(minutes=6)
        await session.execute(update(EmailChallenge).values(expires_at=earlier, sent_at=earlier))
        await session.commit()

    assert (await verify_otp(client, challenge)).json()["code"] == "OTP_EXPIRED"
    monkeypatch.setattr("app.usecase.student_auth.secrets.randbelow", lambda _: 445566)
    assert (await resend_otp(client, challenge)).status_code == 202
    assert (await verify_otp(client, challenge)).json()["code"] == "OTP_INVALID"
    assert (await verify_otp(client, challenge, "445566")).status_code == 201


class FakeGoogle:
    enabled = True

    def __init__(self, identity, challenge):
        self.identity = identity
        self.challenge = challenge

    async def verify_callback(self, code, state):
        assert code == "provider-code" and state == "provider-state"
        return self.identity, self.challenge


async def google_ticket(client, identity):
    verifier = TokenService().generate()
    fake = FakeGoogle(identity, browser_challenge(verifier))
    app.dependency_overrides[get_google_identity] = lambda: fake
    callback = await client.get(
        "/api/auth/google/callback", params={"code": "provider-code", "state": "provider-state"}
    )
    assert callback.status_code == 303
    assert callback.headers["referrer-policy"] == "no-referrer"
    target = urlsplit(callback.headers["location"])
    assert target.path == "/login/google" and not target.query
    return parse_qs(target.fragment)["ticket"][0], verifier


async def exchange(client, ticket, verifier):
    return await client.post(f"{GOOGLE}/exchange", json={"ticket": ticket, "verifier": verifier})


async def test_google_creates_student_and_login_ticket_is_bound_and_single_use(client, db):
    identity = GoogleIdentity("google-1", "new@gmail.com", "Học sinh", True)
    ticket, verifier = await google_ticket(client, identity)
    assert (await exchange(client, ticket, TokenService().generate())).json()["code"] == "GOOGLE_INVALID"

    accepted = await exchange(client, ticket, verifier)
    assert accepted.status_code == 200 and COOKIE in client.cookies
    assert accepted.json()["role"] == "student"
    assert (await exchange(client, ticket, verifier)).json()["code"] == "GOOGLE_INVALID"

    updated = GoogleIdentity("google-1", "new-address@gmail.com", None, True)
    again = await exchange(client, *await google_ticket(client, updated))
    assert again.json()["user_id"] == accepted.json()["user_id"]
    async with db() as session:
        user = (await session.execute(select(User))).scalar_one()
        assert user.google_subject == identity.subject and user.password_hash is None


async def test_google_links_verified_email_and_keeps_password(client, db):
    email = "existing@gmail.com"
    registered = await register(client, email)
    result = await exchange(client, *await google_ticket(client, GoogleIdentity("google-2", email, None, True)))
    assert result.status_code == 200
    assert result.json()["user_id"] == registered.json()["user_id"]
    assert (await login(client, email)).status_code == 200
    conflict = await exchange(client, *await google_ticket(client, GoogleIdentity("google-other", email, None, True)))
    assert conflict.json()["code"] == "GOOGLE_ACCOUNT_CONFLICT"
    async with db() as session:
        assert (await session.execute(select(func.count()).select_from(User))).scalar_one() == 1


async def test_google_links_legacy_email_and_revokes_unverified_credentials(client, db):
    email = "old@gmail.com"
    async with db() as session:
        old = await UserRepository(session).add(email, get_password_service().hash_sync(PW), "student")
    assert (await login(client, email)).status_code == 200
    old_token = client.cookies.pop(COOKIE)

    result = await exchange(client, *await google_ticket(client, GoogleIdentity("google-legacy", email, None, True)))
    assert result.status_code == 200 and result.json()["user_id"] == old.user_id
    client.cookies.clear()
    assert (await login(client, email)).status_code == 401
    rejected = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert rejected.json()["code"] == "SESSION_REVOKED"


async def test_google_for_external_email_verifies_mailbox_first(client):
    identity = GoogleIdentity("google-external", "external@example.com", None, False)
    challenge = await exchange(client, *await google_ticket(client, identity))
    assert challenge.status_code == 202 and COOKIE not in client.cookies
    identifier = challenge.json()["challenge"]
    assert (await verify_otp(client, identifier)).json()["code"] == "INVALID_CHALLENGE"
    signed_in = await verify_otp(client, identifier, purpose="google_email")
    assert signed_in.status_code == 200 and signed_in.json()["email"] == identity.email
    assert COOKIE in client.cookies


async def test_google_cannot_link_admin(client, db):
    admin = await make_admin(db, email="admin@gmail.com")
    identity = GoogleIdentity("google-admin", admin.email, None, True)
    result = await exchange(client, *await google_ticket(client, identity))
    assert result.status_code == 409 and result.json()["code"] == "GOOGLE_ACCOUNT_CONFLICT"
    assert COOKIE not in client.cookies


def test_google_authorization_uses_pkce_and_rejects_modified_state():
    settings = Settings(
        _env_file=None, google_client_id="test-google-client",
        google_client_secret=TokenService().generate(),
        google_callback_url="https://api.example.com/api/auth/google/callback",
        frontend_url="https://app.example.com",
    )
    service = GoogleIdentityService(settings)
    challenge = browser_challenge(TokenService().generate())
    url = urlsplit(service.authorization_url(challenge))
    params = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert params["scope"] == ["openid email profile"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["code_challenge"][0] != challenge
    assert params["redirect_uri"] == [settings.google_callback_url]
    state = params["state"][0]
    assert service._read_state(state)[0] == challenge
    with pytest.raises(GoogleIdentityError):
        service._read_state("a" + state)
