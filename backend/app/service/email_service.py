from base64 import urlsafe_b64encode
from email import policy
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

import httpx

from app.core.config import Settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class EmailConfigurationError(RuntimeError):
    """Email delivery is disabled or incorrectly configured."""


class EmailDeliveryError(RuntimeError):
    """Google did not confirm email delivery submission."""


class GmailEmailService:
    def __init__(
        self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._settings = settings
        self._transport = transport

    async def send(
        self, *, to: str, subject: str, text: str, html: str | None = None, logo: bytes | None = None
    ) -> str:
        """Submit an email with a plain-text fallback and return the Gmail message ID."""
        settings = self._settings
        if settings.email_provider != "gmail":
            raise EmailConfigurationError("Set EMAIL_PROVIDER=gmail to enable email delivery.")

        credentials = {
            "GMAIL_CLIENT_ID": settings.gmail_client_id.get_secret_value().strip(),
            "GMAIL_CLIENT_SECRET": settings.gmail_client_secret.get_secret_value().strip(),
            "GMAIL_REFRESH_TOKEN": settings.gmail_refresh_token.get_secret_value().strip(),
        }
        missing = [name for name, value in credentials.items() if not value]
        if not settings.email_from.strip():
            missing.append("EMAIL_FROM")
        if missing:
            raise EmailConfigurationError(f"Missing email settings: {', '.join(missing)}")

        try:
            sender = _mailbox(settings.email_from, settings.email_from_name)
        except ValueError:
            raise EmailConfigurationError("Invalid EMAIL_FROM or EMAIL_FROM_NAME.") from None

        message = EmailMessage(policy=policy.SMTP)
        message["From"] = sender
        message["To"] = _mailbox(to)
        message["Subject"] = subject
        message["Date"] = formatdate(usegmt=True)
        message["Message-ID"] = make_msgid(domain=sender.domain)
        message.set_content(text, cte="quoted-printable")
        if html is not None:
            message.add_alternative(html, subtype="html", cte="quoted-printable")
            if logo is not None:
                message.get_payload()[-1].add_related(
                    logo, maintype="image", subtype="png", cid="<examind-logo>"
                )
        raw = urlsafe_b64encode(message.as_bytes()).decode("ascii")

        async with httpx.AsyncClient(timeout=10, transport=self._transport) as client:
            token = await _post_for_field(
                client,
                TOKEN_URL,
                "OAuth refresh",
                "access_token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": credentials["GMAIL_CLIENT_ID"],
                    "client_secret": credentials["GMAIL_CLIENT_SECRET"],
                    "refresh_token": credentials["GMAIL_REFRESH_TOKEN"],
                },
            )
            return await _post_for_field(
                client,
                SEND_URL,
                "Gmail send",
                "id",
                headers={"Authorization": f"Bearer {token}"},
                json={"raw": raw},
            )


def _mailbox(address: str, display_name: str = "") -> Address:
    try:
        mailbox = Address(display_name=display_name, addr_spec=address.strip())
    except ValueError:
        raise ValueError("Expected a single email address.") from None
    if not mailbox.username or not mailbox.domain:
        raise ValueError("Expected a single email address.")
    return Address(display_name, mailbox.username, mailbox.domain.encode("idna").decode("ascii"))


async def _post_for_field(
    client: httpx.AsyncClient, url: str, operation: str, field: str, **kwargs
) -> str:
    try:
        response = await client.post(url, **kwargs)
    except httpx.RequestError:
        raise EmailDeliveryError(f"{operation} failed during the HTTP request.") from None
    if not response.is_success:
        raise EmailDeliveryError(f"{operation} failed with HTTP {response.status_code}.")

    try:
        body = response.json()
    except ValueError:
        raise EmailDeliveryError(f"{operation} returned invalid JSON.") from None
    value = body.get(field) if isinstance(body, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise EmailDeliveryError(f"{operation} response is missing {field}.")
    return value
