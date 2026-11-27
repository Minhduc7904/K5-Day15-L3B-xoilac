"""Admin quản lý tài khoản học sinh và admin (issue #20). Không biết HTTP hay socket.

Toàn bộ luật "ai được làm gì với ai" nằm trong hàm thuần `can_manage`, có test riêng cho mọi tổ hợp.
Xoá tài khoản = khoá (status=disabled), không xoá dòng.
Khoá, đặt lại mật khẩu, hạ vai trò → thu hồi mọi phiên và gọi RealtimeNotifier.kick_user.
"""
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from app.models.user import ROLE_ADMIN, ROLE_STUDENT, STATUS_ACTIVE, STATUS_DISABLED, User
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.service.password_service import PasswordService
from app.usecase.auth import (
    PASSWORD_MAX,
    PASSWORD_MIN,
    ROLES,
    AuthError,
    AuthUseCase,
    CurrentUser,
    EmailAlreadyRegistered,
    InvalidInput,
    RoleForbidden,
    normalize_email,
)
from app.usecase.ports import RealtimeNotifier, RevokeReason

Action = Literal["create", "update", "reset_password"]
UPDATABLE_FIELDS = frozenset({"display_name", "email", "role", "status"})
STATUSES = (STATUS_ACTIVE, STATUS_DISABLED)


class UserNotFound(AuthError):
    code = "USER_NOT_FOUND"
    message = "Không có tài khoản này"


class CannotModifyRoot(AuthError):
    code = "CANNOT_MODIFY_ROOT"
    message = "Không thể khóa, đổi vai trò, đổi email hay đặt lại mật khẩu của admin gốc"


class CannotModifySelf(AuthError):
    code = "CANNOT_MODIFY_SELF"
    message = "Không thể tự khóa hoặc tự hạ vai trò của chính mình"


@dataclass(frozen=True)
class Principal:
    """Phần tối thiểu của một tài khoản mà luật phân quyền cần biết."""

    user_id: int
    role: str
    is_root: bool

    @classmethod
    def of(cls, user: User) -> "Principal":
        return cls(user_id=user.user_id, role=user.role, is_root=bool(user.is_root))


def can_manage(
    actor: Principal, target: Principal | None, action: Action, changes: Mapping[str, Any]
) -> type[AuthError] | None:
    """Hàm thuần: trả None nếu được phép, ngược lại trả lớp lỗi (FORBIDDEN_ROLE, CANNOT_MODIFY_ROOT, CANNOT_MODIFY_SELF).

    - actor: admin đang thao tác (đã qua AdminDep).
    - target: tài khoản bị thao tác; None khi action="create".
    - changes: các trường muốn đổi (update) hoặc {"role": ...} của tài khoản sẽ tạo (create).
    Xem (GET) không đi qua hàm này: mọi admin đều xem được.
    """
    if "is_root" in changes:
        return CannotModifyRoot  # không ai đặt is_root qua API

    wants_admin = changes.get("role") == ROLE_ADMIN

    if action == "create":
        return RoleForbidden if wants_admin and not actor.is_root else None

    assert target is not None
    is_self = actor.user_id == target.user_id
    only_name = action == "update" and set(changes) <= {"display_name"}

    # Admin gốc: chỉ chính nó sửa display_name của mình; còn lại không ai được đụng.
    if target.is_root:
        if is_self and only_name:
            return None
        if only_name:
            return RoleForbidden  # admin thường đụng tài khoản admin
        return CannotModifyRoot

    # Không tự khoá, không tự hạ vai trò.
    if is_self and (
        changes.get("status") == STATUS_DISABLED or ("role" in changes and changes["role"] != target.role)
    ):
        return CannotModifySelf

    # Chỉ admin gốc quản lý tài khoản admin (kể cả tài khoản admin của chính mình).
    if target.role == ROLE_ADMIN and not actor.is_root:
        return RoleForbidden

    # Học sinh: mọi admin quản lý được, nhưng chỉ admin gốc nâng học sinh thành admin.
    if wants_admin and target.role != ROLE_ADMIN and not actor.is_root:
        return RoleForbidden
    return None


@dataclass(frozen=True)
class UserPage:
    items: Sequence[User]
    total: int
    page: int
    page_size: int


class UserManagementUseCase:
    def __init__(
        self,
        auth: AuthUseCase,
        users: UserRepository,
        sessions: SessionRepository,
        passwords: PasswordService,
        notifier: RealtimeNotifier,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._auth = auth
        self._users = users
        self._sessions = sessions
        self._passwords = passwords
        self._notifier = notifier
        self._now = now

    async def list_users(
        self, role: str | None, status: str | None, q: str | None, page: int, page_size: int
    ) -> UserPage:
        items, total = await self._users.search(
            role=role, status=status, q=(q or "").strip() or None, offset=(page - 1) * page_size, limit=page_size
        )
        return UserPage(items=items, total=total, page=page, page_size=page_size)

    async def get_user(self, user_id: int) -> User:
        user = await self._users.get(user_id)
        if user is None:
            raise UserNotFound()
        return user

    async def create_user(
        self, actor: CurrentUser, email: str, password: str, role: str, display_name: str | None
    ) -> User:
        if role not in ROLES:
            raise InvalidInput(f"Vai trò không hợp lệ: {role}")
        self._check(Principal.of(actor.user), None, "create", {"role": role})
        # create_user của Auth kiểm độ dài mật khẩu, chuẩn hoá email và trả EMAIL_TAKEN.
        return await self._auth.create_user(email, password, role, display_name, created_by=actor.user_id)

    async def update_user(self, actor: CurrentUser, user_id: int, changes: Mapping[str, Any]) -> User:
        unknown = set(changes) - UPDATABLE_FIELDS
        if unknown:
            raise InvalidInput(f"Không sửa được trường: {', '.join(sorted(unknown))}")
        if "role" in changes and changes["role"] not in ROLES:
            raise InvalidInput(f"Vai trò không hợp lệ: {changes['role']}")
        if "status" in changes and changes["status"] not in STATUSES:
            raise InvalidInput(f"Trạng thái không hợp lệ: {changes['status']}")

        target = await self.get_user(user_id)
        self._check(Principal.of(actor.user), Principal.of(target), "update", changes)

        values = dict(changes)
        if "email" in values:
            values["email"] = normalize_email(values["email"])
            other = await self._users.get_by_email(values["email"])
            if other is not None and other.user_id != target.user_id:
                raise EmailAlreadyRegistered()

        reason: RevokeReason | None = None
        if values.get("status") == STATUS_DISABLED and target.status != STATUS_DISABLED:
            reason = "disabled"
        elif values.get("role") == ROLE_STUDENT and target.role == ROLE_ADMIN:
            reason = "role_changed"

        await self._users.update(target, values)
        if reason is not None:
            await self._revoke_everything(target.user_id, reason)
        return target

    async def reset_password(self, actor: CurrentUser, user_id: int, new_password: str) -> None:
        if not PASSWORD_MIN <= len(new_password) <= PASSWORD_MAX:
            raise InvalidInput(f"Mật khẩu phải dài {PASSWORD_MIN}–{PASSWORD_MAX} ký tự")
        target = await self.get_user(user_id)
        self._check(Principal.of(actor.user), Principal.of(target), "reset_password", {})
        await self._users.update(target, {"password_hash": await self._passwords.hash(new_password)})
        await self._revoke_everything(target.user_id, "password_reset")

    async def _revoke_everything(self, user_id: int, reason: RevokeReason) -> None:
        """Thu hồi mọi phiên trong DB trước, rồi mới đẩy socket ra: kể cả khi đẩy socket lỗi, phiên đã chết."""
        await self._sessions.revoke_all_for_user(user_id, self._now())
        await self._users.commit()
        await self._notifier.kick_user(user_id, reason)

    @staticmethod
    def _check(actor: Principal, target: Principal | None, action: Action, changes: Mapping[str, Any]) -> None:
        error = can_manage(actor, target, action, changes)
        if error is not None:
            raise error()
