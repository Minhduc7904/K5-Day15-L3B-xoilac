import json
from pathlib import Path
from base64 import urlsafe_b64decode
from email import policy
from email.parser import BytesParser
from urllib.parse import parse_qs

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.service.email_templates import verification_email
from app.service.email_service import (
    SEND_URL,
    TOKEN_URL,
    EmailConfigurationError,
    EmailDeliveryError,
    GmailEmailService,
)


@pytest.fixture
def gmail_settings() -> Settings:
    return Settings(
        email_provider="gmail",
        email_from="sender@example.com",
        email_from_name="Examind",
        gmail_client_id=SecretStr("test-client"),
        gmail_client_secret=SecretStr("test-secret"),
        gmail_refresh_token=SecretStr("test-refresh"),
    )


@pytest.mark.asyncio
async def test_send_refreshes_token_and_builds_unicode_mime(gmail_settings):
    requests = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        assert request.method == "POST"
        if str(request.url) == TOKEN_URL:
            assert parse_qs(request.content.decode()) == {
                "grant_type": ["refresh_token"],
                "client_id": ["test-client"],
                "client_secret": ["test-secret"],
                "refresh_token": ["test-refresh"],
            }
            return httpx.Response(200, json={"access_token": "test-access"})

        assert request.headers["Authorization"] == "Bearer test-access"
        payload = urlsafe_b64decode(json.loads(request.content)["raw"])
        message = BytesParser(policy=policy.default).parsebytes(payload)
        assert message["From"] == "Examind <sender@example.com>"
        assert message["To"] == "student@example.com"
        assert message["Subject"] == "Đề ôn tập"
        assert message.get_content().strip() == "Chào bạn!"
        return httpx.Response(200, json={"id": "gmail-message-id"})

    service = GmailEmailService(gmail_settings, transport=httpx.MockTransport(handle))
    assert await service.send(
        to="student@example.com", subject="Đề ôn tập", text="Chào bạn!"
    ) == "gmail-message-id"
    assert requests == [TOKEN_URL, SEND_URL]


def unexpected_request(request: httpx.Request) -> httpx.Response:
    pytest.fail(f"Unexpected HTTP request to {request.url}")


@pytest.mark.asyncio
async def test_missing_oauth_configuration_fails_before_http(gmail_settings):
    gmail_settings.gmail_refresh_token = SecretStr("")
    service = GmailEmailService(gmail_settings, transport=httpx.MockTransport(unexpected_request))
    with pytest.raises(EmailConfigurationError, match="GMAIL_REFRESH_TOKEN"):
        await service.send(to="student@example.com", subject="Title", text="Body")


@pytest.mark.asyncio
async def test_header_injection_fails_before_http(gmail_settings):
    service = GmailEmailService(gmail_settings, transport=httpx.MockTransport(unexpected_request))
    with pytest.raises(ValueError):
        await service.send(
            to="student@example.com", subject="Title\r\nBcc: other@example.com", text="Body"
        )


@pytest.mark.parametrize(
    ("failed_url", "message"),
    [(TOKEN_URL, "OAuth refresh failed with HTTP 401"), (SEND_URL, "Gmail send failed with HTTP 401")],
)
@pytest.mark.asyncio
async def test_google_error_omits_response_body(gmail_settings, failed_url, message):
    requests = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if str(request.url) == failed_url:
            return httpx.Response(401, json={"error_description": "sensitive response"})
        return httpx.Response(200, json={"access_token": "test-access"})

    service = GmailEmailService(gmail_settings, transport=httpx.MockTransport(handle))
    with pytest.raises(EmailDeliveryError) as error:
        await service.send(to="student@example.com", subject="Title", text="Body")
    assert str(error.value) == f"{message}."
    assert requests == ([TOKEN_URL] if failed_url == TOKEN_URL else [TOKEN_URL, SEND_URL])

@pytest.mark.asyncio
async def test_branded_email_contains_plain_text_html_and_inline_logo(gmail_settings):
    content = verification_email("112233", 5, google=False)

    def handle(request: httpx.Request) -> httpx.Response:
        if str(request.url) == TOKEN_URL:
            return httpx.Response(200, json={"access_token": "test-access"})
        payload = urlsafe_b64decode(json.loads(request.content)["raw"])
        message = BytesParser(policy=policy.default).parsebytes(payload)
        assert message["Message-ID"] and message["Date"]
        assert "112233" in message.get_body(("plain",)).get_content()
        assert "cid:examind-logo" in message.get_body(("html",)).get_content()
        logo = next(part for part in message.walk() if part.get_content_type() == "image/png")
        assert logo["Content-ID"] == "<examind-logo>"
        frontend_logo = Path(__file__).resolve().parents[2] / "frontend/public/brand/examind-mark.png"
        assert logo.get_payload(decode=True) == frontend_logo.read_bytes()
        return httpx.Response(200, json={"id": "gmail-message-id"})

    service = GmailEmailService(gmail_settings, transport=httpx.MockTransport(handle))
    assert await service.send(
        to="student@example.com", subject=content.subject, text=content.text, html=content.html, logo=content.logo
    ) == "gmail-message-id"
