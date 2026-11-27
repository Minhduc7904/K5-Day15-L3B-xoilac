"""Luồng xác thực: đăng ký, đăng nhập, đăng xuất, kiểm phiên, kiểm vai trò.

Không biết HTTP: lỗi nghiệp vụ là các lớp AuthError có `code`; lớp API đổi sang mã HTTP.
Không log mật khẩu hay token.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.models.session import UserSession
from app.models.user import ROLE_ADMIN, ROLE_STUDENT, STATUS_ACTIVE, User
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import DuplicateEmailError, UserRepository
from app.service.password_service import PasswordService
from app.service.token_service import TokenService

ROLES = (ROLE_STUDENT, ROLE_ADMIN)
PASSWORD_MIN = 6
PASSWORD_MAX = 128


class AuthError(Exception):
    code = "AUTH_ERROR"
    message = "Lỗi xác thực"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message


class EmailAlreadyRegistered(AuthError):
    code = "EMAIL_TAKEN"
    message = "Email này đã được đăng ký"


class InvalidCredentials(AuthError):
    code = "INVALID_CREDENTIALS"
    message = "Email hoặc mật khẩu không đúng"


class AccountDisabled(AuthError):
    code = "ACCOUNT_DISABLED"
    message = "Tài khoản đã bị khóa"


class SessionMissing(AuthError):
    code = "SESSION_MISSING"
    message = "Chưa đăng nhập"


class SessionInvalid(AuthError):
    code = "SESSION_INVALID"
    message = "Phiên không hợp lệ"


class SessionExpired(AuthError):
    code = "SESSION_EXPIRED"
    message = "Phiên đã hết hạn, hãy đăng nhập lại"


class SessionRevoked(AuthError):
    code = "SESSION_REVOKED"
    message = "Phiên đã bị đăng xuất, hãy đăng nhập lại"


class RoleForbidden(AuthError):
    code = "FORBIDDEN_ROLE"
    message = "Tài khoản không có quyền dùng chức năng này"


class InvalidInput(AuthError):
    code = "INVALID_INPUT"
    message = "Dữ liệu không hợp lệ"


@dataclass(frozen=True)
class CurrentUser:
    """Người dùng của request hiện tại, kèm phiên đang dùng."""

    user: User
    session_id: int

    @property
    def user_id(self) -> int:
        return self.user.user_id

    @property
    def role(self) -> str:
        return self.user.role


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _aware(dt: datetime) -> datetime:
    # SQLite (test) trả datetime không có múi giờ; PostgreSQL trả timestamptz. Coi mọi giá trị là UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def ensure_role(current: CurrentUser, *roles: str) -> CurrentUser:
    if current.role not in roles:
        raise RoleForbidden()
    return current


class AuthUseCase:
    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        passwords: PasswordService,
        tokens: TokenService,
        session_ttl_hours: int,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._passwords = passwords
        self._tokens = tokens
        self._ttl = timedelta(hours=session_ttl_hours)
        self._now = now

    async def register(
        self, email: str, password: str, display_name: str | None = None, user_agent: str | None = None
    ) -> tuple[User, str]:
        """Đăng ký công khai: luôn tạo student và mở phiên. Trả (user, token)."""
        user = await self.create_user(email, password, ROLE_STUDENT, display_name)
        token = await self._open_session(user, user_agent)
        return user, token

    async def create_user(
        self,
        email: str,
        password: str,
        role: str,
        display_name: str | None = None,
        created_by: int | None = None,
    ) -> User:
        """Tạo tài khoản. Chỉ được gọi từ: register (student), CLI create_admin / ensure_admin (admin,
        created_by=None) và AdminAccountsUseCase.create_admin (admin, created_by = admin đang thao tác)."""
        if role not in ROLES:
            raise InvalidInput(f"Vai trò không hợp lệ: {role}")
        if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
            raise InvalidInput(f"Mật khẩu phải dài {PASSWORD_MIN}–{PASSWORD_MAX} ký tự")
        email = normalize_email(email)
        if await self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegistered()
        password_hash = await self._passwords.hash(password)
        try:
            return await self._users.add(email, password_hash, role, display_name, created_by)
        except DuplicateEmailError:
            # Hai request đăng ký cùng email chạy song song.
            raise EmailAlreadyRegistered() from None

    async def login(self, email: str, password: str, user_agent: str | None = None) -> tuple[User, str]:
        user = await self._users.get_by_email(normalize_email(email))
        if user is None:
            await self._passwords.verify_dummy(password)
            raise InvalidCredentials()
        if not await self._passwords.verify(user.password_hash, password):
            raise InvalidCredentials()
        # Chỉ báo khóa khi mật khẩu đúng, để người ngoài không dò được tài khoản nào bị khóa.
        if user.status != STATUS_ACTIVE:
            raise AccountDisabled()
        await self._users.set_last_login(user, self._now())
        token = await self._open_session(user, user_agent)
        return user, token

    async def get_current_user(self, token: str | None) -> CurrentUser:
        """Kiểm phiên: tồn tại, chưa thu hồi, chưa hết hạn, user còn active. Cập nhật last_used_at."""
        row, user = await self._load_session(token)
        if user.status != STATUS_ACTIVE:
            raise AccountDisabled()
        await self._sessions.touch(row, self._now())
        return CurrentUser(user=user, session_id=row.session_id)

    async def logout(self, current: CurrentUser) -> None:
        """Thu hồi phiên của request hiện tại (đã qua get_current_user). Có hiệu lực ngay."""
        await self._sessions.revoke(current.session_id, self._now())

    async def _load_session(self, token: str | None) -> tuple[UserSession, User]:
        if not token:
            raise SessionMissing()
        found = await self._sessions.get_with_user(self._tokens.hash(token))
        if found is None:
            raise SessionInvalid()
        row, user = found
        if row.revoked_at is not None:
            raise SessionRevoked()
        if _aware(row.expires_at) <= self._now():
            raise SessionExpired()
        return row, user

    async def _open_session(self, user: User, user_agent: str | None) -> str:
        token = self._tokens.generate()
        await self._sessions.add(
            user_id=user.user_id,
            token_hash=self._tokens.hash(token),
            expires_at=self._now() + self._ttl,
            user_agent=(user_agent or None) and user_agent[:255],
        )
        return token
