"""Admin gốc từ biến môi trường ADMIN_* (issue #8, mở rộng ở #20).

Chỉ lệnh `python -m app.cli.ensure_admin` (chạy trong db-init) gọi usecase này. Không biết HTTP.
"""
from enum import Enum

from app.models.user import ROLE_ADMIN, User
from app.repositories.user_repository import DuplicateRootError, UserRepository
from app.usecase.auth import (
    PASSWORD_MAX,
    PASSWORD_MIN,
    AuthError,
    AuthUseCase,
    EmailAlreadyRegistered,
    InvalidInput,
    normalize_email,
)

# Mật khẩu admin mặc định trên prod (COOKIE_SECURE=true) phải dài hơn mức tối thiểu chung.
PROD_ADMIN_PASSWORD_MIN = 12


class EmailBelongsToNonAdmin(AuthError):
    code = "EMAIL_NOT_ADMIN"
    message = "Email này đang thuộc một tài khoản không phải admin; không tự nâng quyền"


class EnsureResult(Enum):
    SKIPPED = "skipped"
    CREATED = "created"  # tạo admin mới, là admin gốc
    ALREADY_ROOT = "already_root"  # email đã là admin gốc: không đổi gì
    MARKED_ROOT = "marked_root"  # email là admin thường, hệ thống chưa có gốc: đánh dấu làm gốc
    OTHER_ROOT = "other_root"  # đã có admin gốc khác: không đổi gì, không tạo


class DefaultAdminUseCase:
    def __init__(self, auth: AuthUseCase, users: UserRepository) -> None:
        self._auth = auth
        self._users = users

    async def ensure_default_admin(
        self, email: str, password: str, display_name: str | None, strict: bool
    ) -> tuple[EnsureResult, User | None]:
        """Tạo admin gốc từ ADMIN_EMAIL nếu chưa có (#20). Idempotent, không bao giờ đổi mật khẩu hay status.

        - Chưa có tài khoản và chưa có admin gốc: tạo admin, đặt is_root.
        - Email là admin thường và chưa có admin gốc: đánh dấu làm gốc.
        - Email đã là gốc, hoặc đã có gốc khác: không đổi gì (OTHER_ROOT để CLI cảnh báo).
        - Email đang thuộc student: EmailBelongsToNonAdmin, không nâng quyền.
        `strict` (prod) đòi mật khẩu ≥ PROD_ADMIN_PASSWORD_MIN.
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
        if existing is not None and existing.role != ROLE_ADMIN:
            raise EmailBelongsToNonAdmin()
        if existing is not None and existing.is_root:
            return EnsureResult.ALREADY_ROOT, existing

        # Từ đây: email là admin thường, hoặc chưa có tài khoản. Không bao giờ đổi mật khẩu hay status.
        root = await self._users.get_root()
        if root is not None:
            # Đã có admin gốc khác: không tạo thêm admin, không chuyển quyền gốc.
            return EnsureResult.OTHER_ROOT, root
        if existing is None:
            try:
                existing = await self._auth.create_user(email, password, ROLE_ADMIN, display_name, created_by=None)
            except EmailAlreadyRegistered:
                # Một tiến trình khác vừa tạo cùng email: đọc lại.
                existing = await self._users.get_by_email(email)
                if existing is None or existing.role != ROLE_ADMIN:
                    raise EmailBelongsToNonAdmin() from None
            result = EnsureResult.CREATED
        else:
            result = EnsureResult.MARKED_ROOT
        try:
            await self._users.set_root(existing)
        except DuplicateRootError:
            # Tiến trình khác vừa đặt admin gốc trước.
            return EnsureResult.OTHER_ROOT, await self._users.get_root()
        return result, existing
