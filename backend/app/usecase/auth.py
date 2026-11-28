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
from app.service.google_identity import GoogleIdentity
from app.service.password_service import PasswordService
from app.service.token_service import TokenService
from app.usecase.realtime_notifier import RealtimeNotifier

ROLES = (ROLE_STUDENT, ROLE_ADMIN)
# Mật khẩu MỚI phải dài 8–128 ký tự (từ review PR #17; trước đó là 6). Đăng nhập không kiểm độ dài,
# nên tài khoản đã đặt mật khẩu 6–7 ký tự trước khi đổi luật vẫn đăng nhập được.
PASSWORD_MIN = 8
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


class GoogleAccountConflict(AuthError):
    code = "GOOGLE_ACCOUNT_CONFLICT"
    message = "Email này không thể liên kết với tài khoản Google này"


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


def validate_session(
    found: tuple[UserSession, User] | None, now: datetime,
) -> tuple[UserSession, User]:
    if found is None:
        raise SessionInvalid()
    row, user = found
    if row.revoked_at is not None:
        raise SessionRevoked()
    if _aware(row.expires_at) <= now:
        raise SessionExpired()
    if user.status != STATUS_ACTIVE:
        raise AccountDisabled()
    return row, user


class AuthUseCase:
    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        passwords: PasswordService,
        tokens: TokenService,
        session_ttl_hours: int,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        realtime: RealtimeNotifier | None = None,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._passwords = passwords
        self._tokens = tokens
        self._ttl = timedelta(hours=session_ttl_hours)
        self._now = now
        self._realtime = realtime

    async def prepare_registration(self, email: str, password: str) -> str:
        if await self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegistered()
        return await self._passwords.hash(password)

    async def register_verified(
        self, email: str, password_hash: str, display_name: str | None, user_agent: str | None
    ) -> tuple[User, str]:
        try:
            user = await self._users.add(
                email, password_hash, ROLE_STUDENT, display_name, verified_at=self._now(), commit=False
            )
        except DuplicateEmailError:
            raise EmailAlreadyRegistered() from None
        return user, await self._open_session(user, user_agent)

    async def create_user(
        self,
        email: str,
        password: str,
        role: str,
        display_name: str | None = None,
        created_by: int | None = None,
    ) -> User:
        """Tạo tài khoản. Được dùng bởi CLI create_admin / ensure_admin (admin,
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
        user = await self._users.get_by_email(normalize_email(email), lock=True)
        if user is None or user.password_hash is None:
            await self._passwords.verify_dummy(password)
            raise InvalidCredentials()
        if not await self._passwords.verify(user.password_hash, password):
            raise InvalidCredentials()
        # Chỉ báo khóa khi mật khẩu đúng, để người ngoài không dò được tài khoản nào bị khóa.
        if user.status != STATUS_ACTIVE:
            raise AccountDisabled()
        user.last_login_at = self._now()
        token = await self._open_session(user, user_agent)
        return user, token

    async def has_google_account(self, subject: str) -> bool:
        return await self._users.get_by_google_subject(subject) is not None

    async def google_login(self, identity: GoogleIdentity, user_agent: str | None) -> tuple[User, str]:
        user = await self._users.get_by_google_subject(identity.subject, lock=True)
        if user is None:
            user = await self._users.get_by_email(identity.email, lock=True)
        if user is None:
            try:
                user = await self._users.add(
                    identity.email, None, ROLE_STUDENT, identity.name,
                    verified_at=self._now(), google_subject=identity.subject, commit=False,
                )
            except DuplicateEmailError:
                user = await self._users.get_by_google_subject(identity.subject, lock=True)
                if user is None:
                    user = await self._users.get_by_email(identity.email, lock=True)
                if user is None:
                    raise GoogleAccountConflict() from None

        if user.role != ROLE_STUDENT or user.google_subject not in (None, identity.subject):
            raise GoogleAccountConflict()
        if user.status != STATUS_ACTIVE:
            raise AccountDisabled()
        revoke_old_sockets = user.google_subject is None and user.email_verified_at is None
        if user.google_subject is None:
            if revoke_old_sockets:
                # A legacy password may have been set by someone who never owned the address.
                await self._sessions.revoke_all_for_user(user.user_id, self._now())
            try:
                await self._users.link_google(user, identity.subject, self._now())
            except DuplicateEmailError:
                raise GoogleAccountConflict() from None
        user.last_login_at = self._now()
        token = await self._open_session(user, user_agent)
        if revoke_old_sockets:
            await self.revoke_user_sockets(user.user_id)
        return user, token

    async def password_reset_candidate(self, email: str) -> User | None:
        """Tài khoản được tự đặt lại mật khẩu qua email: học sinh đang hoạt động. Admin dùng CLI."""
        user = await self._users.get_by_email(normalize_email(email))
        if user is None or user.role != ROLE_STUDENT or user.status != STATUS_ACTIVE:
            return None
        return user

    async def set_password(self, user_id: int, password: str) -> bool:
        """Đặt mật khẩu mới, thu hồi mọi phiên cũ rồi commit. Trả False nếu tài khoản không còn hợp lệ."""
        if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
            raise InvalidInput(f"Mật khẩu phải dài {PASSWORD_MIN}–{PASSWORD_MAX} ký tự")
        user = await self._users.get(user_id)
        if user is None or user.role != ROLE_STUDENT or user.status != STATUS_ACTIVE:
            return False
        user.password_hash = await self._passwords.hash(password)
        if user.email_verified_at is None:
            user.email_verified_at = self._now()
        await self._sessions.revoke_all_for_user(user.user_id, self._now())
        await self._users.commit()
        await self.revoke_user_sockets(user.user_id)
        return True

    async def revoke_user_sockets(self, user_id: int) -> None:
        if self._realtime is not None:
            await self._realtime.revoke_user(user_id)

    async def get_current_user(self, token: str | None) -> CurrentUser:
        """Kiểm phiên: tồn tại, chưa thu hồi, chưa hết hạn, user còn active. Cập nhật last_used_at."""
        row, user = await self._load_session(token)
        await self._sessions.touch(row, self._now())
        return CurrentUser(user=user, session_id=row.session_id)

    async def logout(self, token: str | None) -> None:
        """Đăng xuất idempotent: không bao giờ lỗi. Thu hồi phiên nếu token khớp một phiên chưa thu hồi
        (kể cả phiên đã hết hạn hoặc của tài khoản bị khoá). Không có token hoặc token lạ: không làm gì."""
        if not token:
            return
        found = await self._sessions.get_with_user(self._tokens.hash(token))
        if found is None:
            return
        row, _ = found
        if row.revoked_at is None:
            await self._sessions.revoke(row.session_id, self._now())
        if self._realtime is not None:
            await self._realtime.revoke_session(row.session_id)

    async def _load_session(self, token: str | None) -> tuple[UserSession, User]:
        if not token:
            raise SessionMissing()
        found = await self._sessions.get_with_user(self._tokens.hash(token))
        return validate_session(found, self._now())

    async def _open_session(self, user: User, user_agent: str | None) -> str:
        token = self._tokens.generate()
        await self._sessions.add(
            user_id=user.user_id,
            token_hash=self._tokens.hash(token),
            expires_at=self._now() + self._ttl,
            user_agent=(user_agent or None) and user_agent[:255],
        )
        return token
