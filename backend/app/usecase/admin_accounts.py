"""Cấp và quản lý tài khoản admin (issue #8, phần bổ sung).

Quyền admin chỉ đến từ hai nguồn:
1. Người vận hành máy chủ: ensure_default_admin (biến ADMIN_*, chạy trong db-init) hoặc CLI create_admin.
2. Một admin đang active, đã đăng nhập và nhập lại mật khẩu của chính mình: create_admin, set_status.

Không có hàm nào nâng student thành admin. Không biết HTTP; lỗi là AuthError có `code`.
"""
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from enum import Enum

from app.models.user import ROLE_ADMIN, STATUS_ACTIVE, STATUS_DISABLED, User
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.service.password_service import PasswordService
from app.usecase.auth import (
    PASSWORD_MAX,
    PASSWORD_MIN,
    AuthError,
    AuthUseCase,
    CurrentUser,
    EmailAlreadyRegistered,
    InvalidInput,
    normalize_email,
)

# Mật khẩu admin mặc định trên prod (COOKIE_SECURE=true) phải dài hơn mức tối thiểu chung.
PROD_ADMIN_PASSWORD_MIN = 12
STATUSES = (STATUS_ACTIVE, STATUS_DISABLED)


class ReauthFailed(AuthError):
    code = "REAUTH_FAILED"
    message = "Mật khẩu xác nhận không đúng"


class CannotModifySelf(AuthError):
    code = "CANNOT_MODIFY_SELF"
    message = "Không thể đổi trạng thái tài khoản của chính mình"


class LastAdmin(AuthError):
    code = "LAST_ADMIN"
    message = "Không thể khóa admin đang hoạt động cuối cùng"


class AccountNotFound(AuthError):
    code = "ACCOUNT_NOT_FOUND"
    message = "Không có tài khoản admin này"


class EmailBelongsToNonAdmin(AuthError):
    code = "EMAIL_NOT_ADMIN"
    message = "Email này đang thuộc một tài khoản không phải admin; không tự nâng quyền"


class EnsureResult(Enum):
    SKIPPED = "skipped"
    CREATED = "created"
    ALREADY_ADMIN = "already_admin"


class AdminAccountsUseCase:
    def __init__(
        self,
        auth: AuthUseCase,
        users: UserRepository,
        sessions: SessionRepository,
        passwords: PasswordService,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._auth = auth
        self._users = users
        self._sessions = sessions
        self._passwords = passwords
        self._now = now

    # ---- Người vận hành ----------------------------------------------------------

    async def ensure_default_admin(
        self, email: str, password: str, display_name: str | None, strict: bool
    ) -> tuple[EnsureResult, User | None]:
        """Tạo admin mặc định nếu chưa có. Idempotent: admin đã có thì không đổi gì (kể cả mật khẩu, status).

        `strict` (prod) đòi mật khẩu ≥ PROD_ADMIN_PASSWORD_MIN. Email đang thuộc student: không nâng quyền.
        """
        email = normalize_email(email)
        if not email or not password:
            return EnsureResult.SKIPPED, None
        # Kiểm cấu hình trước, kể cả khi admin đã có: cấu hình sai thì báo ngay ở mọi lần chạy.
        if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
            raise InvalidInput(f"ADMIN_PASSWORD phải dài {PASSWORD_MIN}–{PASSWORD_MAX} ký tự")
        if strict and len(password) < PROD_ADMIN_PASSWORD_MIN:
            raise InvalidInput(
                f"ADMIN_PASSWORD trên prod (COOKIE_SECURE=true) phải dài ít nhất {PROD_ADMIN_PASSWORD_MIN} ký tự"
            )

        existing = await self._users.get_by_email(email)
        if existing is not None:
            if existing.role == ROLE_ADMIN:
                return EnsureResult.ALREADY_ADMIN, existing
            raise EmailBelongsToNonAdmin()
        try:
            user = await self._auth.create_user(email, password, ROLE_ADMIN, display_name, created_by=None)
        except EmailAlreadyRegistered:
            # Một tiến trình khác vừa tạo cùng email: đọc lại để trả kết quả đúng.
            existing = await self._users.get_by_email(email)
            if existing is not None and existing.role == ROLE_ADMIN:
                return EnsureResult.ALREADY_ADMIN, existing
            raise EmailBelongsToNonAdmin() from None
        return EnsureResult.CREATED, user

    # ---- Admin đã đăng nhập --------------------------------------------------------

    async def list_admins(self) -> Sequence[User]:
        return await self._users.list_by_role(ROLE_ADMIN)

    async def create_admin(
        self,
        actor: CurrentUser,
        email: str,
        password: str,
        display_name: str | None,
        current_password: str,
    ) -> User:
        """Admin tạo admin khác. Email đã có (kể cả student) → EMAIL_TAKEN, không nâng quyền."""
        await self._reauth(actor, current_password)
        return await self._auth.create_user(email, password, ROLE_ADMIN, display_name, created_by=actor.user_id)

    async def set_status(self, actor: CurrentUser, user_id: int, status: str, current_password: str) -> User:
        """Khoá hoặc mở khoá một admin khác. Khoá thì thu hồi mọi phiên của người đó.

        Thứ tự: nhập lại mật khẩu → tài khoản đích là admin → (khi khoá) không phải admin active cuối cùng
        → không phải chính mình. Kiểm "admin cuối" trong cùng transaction, sau khi khoá các dòng admin
        (SELECT ... FOR UPDATE), nên hai request khoá lẫn nhau cùng lúc không cùng lọt qua.
        """
        if status not in STATUSES:
            raise InvalidInput(f"Trạng thái không hợp lệ: {status}")
        await self._reauth(actor, current_password)

        try:
            target = await self._users.get(user_id)
            if target is None or target.role != ROLE_ADMIN:
                raise AccountNotFound()

            if status == STATUS_DISABLED:
                admins = await self._users.lock_by_role(ROLE_ADMIN)
                target = next((a for a in admins if a.user_id == user_id), None)
                if target is None or target.role != ROLE_ADMIN:
                    raise AccountNotFound()
                active = [a for a in admins if a.status == STATUS_ACTIVE]
                if target.status == STATUS_ACTIVE and len(active) <= 1:
                    raise LastAdmin()

            if target.user_id == actor.user_id:
                raise CannotModifySelf()

            if target.status != status:
                await self._users.set_status(target, status)
                if status == STATUS_DISABLED:
                    await self._sessions.revoke_all_for_user(target.user_id, self._now())
            await self._users.commit()
        except BaseException:
            await self._users.rollback()  # nhả khoá dòng
            raise
        return target

    async def _reauth(self, actor: CurrentUser, current_password: str) -> None:
        password_hash = actor.user.password_hash
        if not current_password or not password_hash or not await self._passwords.verify(password_hash, current_password):
            raise ReauthFailed()
