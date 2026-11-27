import hmac
import secrets
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from app.models.auth_challenge import EmailChallenge
from app.models.user import User
from app.repositories.auth_challenge_repository import AuthChallengeRepository
from app.service.email_service import EmailConfigurationError, EmailDeliveryError, GmailEmailService
from app.service.email_templates import verification_email
from app.service.google_identity import GoogleIdentity, browser_challenge
from app.service.token_service import TokenService
from app.usecase.auth import AuthError, AuthUseCase, _aware

REGISTRATION = "registration"
GOOGLE_EMAIL = "google_email"
OTP_TTL_MINUTES = 5
RESEND_SECONDS = 60
MAX_ATTEMPTS = 5
MAX_SENDS_PER_HOUR = 5


class InvalidOtp(AuthError):
    code = "OTP_INVALID"
    message = "Mã xác minh chưa đúng"


class ExpiredOtp(AuthError):
    code = "OTP_EXPIRED"
    message = "Mã đã hết hạn. Hãy gửi lại mã mới."


class InvalidChallenge(AuthError):
    code = "INVALID_CHALLENGE"
    message = "Yêu cầu xác minh không còn hiệu lực. Hãy bắt đầu lại."


class TooManyAttempts(AuthError):
    code = "TOO_MANY_ATTEMPTS"
    message = "Bạn đã nhập sai quá nhiều lần. Hãy gửi lại mã mới."


class ResendLimited(AuthError):
    code = "OTP_RESEND_LIMIT"
    message = "Hãy đợi trước khi yêu cầu mã mới. Mỗi email nhận tối đa 5 mã mỗi giờ."


class EmailUnavailable(AuthError):
    code = "EMAIL_UNAVAILABLE"
    message = "Chưa gửi được mã xác minh. Bạn thử lại sau nhé."


class InvalidGoogleLogin(AuthError):
    code = "GOOGLE_INVALID"
    message = "Không xác minh được đăng nhập Google. Hãy bắt đầu lại."


@dataclass(frozen=True)
class PendingVerification:
    challenge: str
    email: str
    expires_in: int = OTP_TTL_MINUTES * 60
    resend_after: int = RESEND_SECONDS


class StudentAuthUseCase:
    def __init__(
        self,
        auth: AuthUseCase,
        challenges: AuthChallengeRepository,
        emails: GmailEmailService,
        tokens: TokenService,
        otp_secret: str,
    ) -> None:
        self._auth = auth
        self._challenges = challenges
        self._emails = emails
        self._tokens = tokens
        self._otp_secret = otp_secret.encode()

    def _otp_digest(self, key: str, otp: str) -> str:
        if len(self._otp_secret) < 32:
            raise EmailUnavailable()
        return hmac.digest(self._otp_secret, f"{key}:{otp}".encode(), "sha256").hex()

    async def start_registration(
        self, email: str, password: str, display_name: str | None
    ) -> PendingVerification:
        password_hash = await self._auth.prepare_registration(email, password)
        return await self._start(
            REGISTRATION, email, {"password_hash": password_hash, "display_name": display_name}
        )

    async def _start(self, purpose: str, email: str, payload: dict) -> PendingVerification:
        now = datetime.now(UTC)
        await self._challenges.delete_stale_challenges(now - timedelta(days=1))
        row = await self._challenges.lock_email(purpose, email)
        row.payload = payload
        return await self._send_code(row, self._tokens.generate(), now)

    async def resend(self, purpose: str, challenge: str) -> PendingVerification:
        row = await self._lock_challenge(purpose, challenge)
        return await self._send_code(row, challenge, datetime.now(UTC))

    async def _send_code(self, row: EmailChallenge, challenge: str, now: datetime) -> PendingVerification:
        if row.sent_at and _aware(row.sent_at) + timedelta(seconds=RESEND_SECONDS) > now:
            raise ResendLimited()
        if row.window_start is None or _aware(row.window_start) + timedelta(hours=1) <= now:
            row.window_start = now
            row.sends = 0
        if row.sends >= MAX_SENDS_PER_HOUR:
            raise ResendLimited()

        code = f"{secrets.randbelow(1_000_000):06d}"
        digest = self._tokens.hash(challenge)
        otp_hash = self._otp_digest(digest, code)
        row.challenge_hash = digest
        row.otp_hash = otp_hash
        row.sent_at = now
        row.expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)
        row.sends += 1
        row.attempts = 0
        email, purpose = row.email, row.purpose
        await self._challenges.commit()

        content = verification_email(code, OTP_TTL_MINUTES, google=purpose == GOOGLE_EMAIL)
        try:
            await self._emails.send(
                to=email, subject=content.subject, text=content.text, html=content.html, logo=content.logo
            )
        except (EmailConfigurationError, EmailDeliveryError):
            latest = await self._challenges.lock_challenge(purpose, digest)
            if latest is not None and latest.otp_hash == otp_hash:
                latest.otp_hash = None
                latest.expires_at = now
                latest.sent_at = None
                await self._challenges.commit()
            raise EmailUnavailable() from None
        return PendingVerification(challenge, email)

    async def _lock_challenge(self, purpose: str, challenge: str) -> EmailChallenge:
        row = await self._challenges.lock_challenge(purpose, self._tokens.hash(challenge))
        if row is None or row.payload is None:
            raise InvalidChallenge()
        return row

    async def verify_email(
        self, purpose: str, challenge: str, otp: str, user_agent: str | None
    ) -> tuple[User, str]:
        row = await self._lock_challenge(purpose, challenge)
        if row.expires_at is None or _aware(row.expires_at) <= datetime.now(UTC) or row.otp_hash is None:
            raise ExpiredOtp()
        if row.attempts >= MAX_ATTEMPTS:
            raise TooManyAttempts()
        expected = self._otp_digest(self._tokens.hash(challenge), otp)
        if not hmac.compare_digest(row.otp_hash, expected):
            row.attempts += 1
            error = TooManyAttempts() if row.attempts == MAX_ATTEMPTS else InvalidOtp()
            await self._challenges.commit()
            raise error

        payload = row.payload
        row.payload = row.otp_hash = row.challenge_hash = None
        if purpose == REGISTRATION:
            return await self._auth.register_verified(
                row.email, payload["password_hash"], payload["display_name"], user_agent
            )
        return await self._auth.google_login(GoogleIdentity(**payload), user_agent)

    async def save_google_handoff(self, identity: GoogleIdentity, challenge: str) -> str:
        ticket = self._tokens.generate()
        now = datetime.now(UTC)
        await self._challenges.save_handoff(
            self._tokens.hash(ticket), challenge, asdict(identity), now + timedelta(minutes=2), now
        )
        return ticket

    async def exchange_google_handoff(
        self, ticket: str, verifier: str, user_agent: str | None
    ) -> tuple[User, str] | PendingVerification:
        payload = await self._challenges.take_handoff(
            self._tokens.hash(ticket), browser_challenge(verifier), datetime.now(UTC)
        )
        if payload is None:
            raise InvalidGoogleLogin()
        identity = GoogleIdentity(**payload)
        if identity.authoritative or await self._auth.has_google_account(identity.subject):
            return await self._auth.google_login(identity, user_agent)
        return await self._start(GOOGLE_EMAIL, identity.email, payload)
