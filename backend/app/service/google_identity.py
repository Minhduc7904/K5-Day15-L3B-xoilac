import base64
import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass
from functools import partial
from time import time
from urllib.parse import urlencode, urlsplit

import httpx
from email_validator import EmailNotValidError, validate_email
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.id_token import verify_oauth2_token
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
OPAQUE_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")


class GoogleConfigurationError(RuntimeError):
    pass


class GoogleIdentityError(RuntimeError):
    pass


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def browser_challenge(verifier: str) -> str:
    return _encode(hashlib.sha256(verifier.encode("ascii")).digest())


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str | None
    authoritative: bool


class GoogleIdentityService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        settings = self._settings
        return bool(
            settings.google_client_id
            and len(settings.google_client_secret.get_secret_value()) >= 16
            and self._valid_url(settings.google_callback_url, origin_only=False)
            and self._valid_url(settings.frontend_url, origin_only=True)
        )

    @staticmethod
    def _valid_url(value: str, *, origin_only: bool) -> bool:
        parts = urlsplit(value)
        local = parts.scheme == "http" and parts.hostname in ("localhost", "127.0.0.1")
        return bool(
            (parts.scheme == "https" or local)
            and parts.hostname
            and not (parts.username or parts.password or parts.query or parts.fragment)
            and (not origin_only or parts.path in ("", "/"))
        )

    def _require_configuration(self) -> None:
        if not self.enabled:
            raise GoogleConfigurationError("Google Sign-In is not configured.")

    def _derive(self, purpose: bytes, data: bytes) -> str:
        key = self._settings.google_client_secret.get_secret_value().encode()
        return _encode(hmac.digest(key, purpose + b":" + data, "sha256"))

    def authorization_url(self, challenge: str) -> str:
        self._require_configuration()
        seed = secrets.token_urlsafe(24)
        state_data = _encode(json.dumps([challenge, int(time()) + 600, seed], separators=(",", ":")).encode())
        signature = self._derive(b"state", state_data.encode())
        return AUTHORIZE_URL + "?" + urlencode(
            {
                "client_id": self._settings.google_client_id,
                "redirect_uri": self._settings.google_callback_url,
                "response_type": "code",
                "scope": "openid email profile",
                "prompt": "select_account",
                "state": f"{state_data}.{signature}",
                "nonce": self._derive(b"nonce", seed.encode()),
                "code_challenge": browser_challenge(self._derive(b"pkce", seed.encode())),
                "code_challenge_method": "S256",
            }
        )

    def _read_state(self, state: str) -> tuple[str, str]:
        try:
            data, signature = state.split(".", 1)
            if not OPAQUE_TOKEN.fullmatch(signature):
                raise ValueError
            if not hmac.compare_digest(self._derive(b"state", data.encode()), signature):
                raise ValueError
            challenge, expires, seed = json.loads(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)))
            if expires <= time() or not OPAQUE_TOKEN.fullmatch(challenge):
                raise ValueError
        except (ValueError, TypeError):
            raise GoogleIdentityError("Invalid or expired OAuth state.") from None
        return challenge, seed

    async def verify_callback(self, code: str, state: str) -> tuple[GoogleIdentity, str]:
        self._require_configuration()
        challenge, seed = self._read_state(state)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self._settings.google_client_id,
                        "client_secret": self._settings.google_client_secret.get_secret_value(),
                        "redirect_uri": self._settings.google_callback_url,
                        "grant_type": "authorization_code",
                        "code_verifier": self._derive(b"pkce", seed.encode()),
                    },
                )
                response.raise_for_status()
                token = response.json()["id_token"]
            claims = await run_in_threadpool(
                verify_oauth2_token,
                token,
                partial(Request(), timeout=5),
                self._settings.google_client_id,
            )
        except (httpx.HTTPError, GoogleAuthError, ValueError, KeyError, TypeError):
            raise GoogleIdentityError("Google token verification failed.") from None

        if claims.get("nonce") != self._derive(b"nonce", seed.encode()) or claims.get("email_verified") is not True:
            raise GoogleIdentityError("Google did not verify this email.")
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject or len(subject) > 255:
            raise GoogleIdentityError("Google did not return a valid subject.")
        try:
            email = validate_email(
                claims.get("email") or "", check_deliverability=False, allow_smtputf8=False
            ).normalized.lower()
        except (EmailNotValidError, TypeError):
            raise GoogleIdentityError("Google did not return a valid email.") from None
        if len(email) > 255:
            raise GoogleIdentityError("Google email is too long.")
        name = claims.get("name")
        name = name.strip()[:100] or None if isinstance(name, str) else None
        authoritative = email.endswith("@gmail.com") or bool(claims.get("hd"))
        return GoogleIdentity(subject, email, name, authoritative), challenge
