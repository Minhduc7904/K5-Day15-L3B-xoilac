from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import to_api_error
from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.repositories.auth_challenge_repository import AuthChallengeRepository
from app.repositories.sample_item_repository import SampleItemRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.service.email_service import GmailEmailService
from app.service.google_identity import GoogleIdentityService
from app.service.password_service import PasswordService
from app.service.storage_service import StorageService
from app.service.token_service import TokenService
from app.usecase.admin_accounts import AdminAccountsUseCase
from app.usecase.auth import AuthError, AuthUseCase, CurrentUser, ensure_role
from app.usecase.sample_files import SampleFileUseCase
from app.usecase.sample_items import SampleItemUseCase
from app.usecase.student_auth import StudentAuthUseCase

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def get_storage() -> StorageService:
    return StorageService(get_settings())


def get_email_service(settings: SettingsDep) -> GmailEmailService:
    return GmailEmailService(settings)


def get_google_identity(settings: SettingsDep) -> GoogleIdentityService:
    return GoogleIdentityService(settings)


GoogleIdentityDep = Annotated[GoogleIdentityService, Depends(get_google_identity)]
EmailServiceDep = Annotated[GmailEmailService, Depends(get_email_service)]
StorageDep = Annotated[StorageService, Depends(get_storage)]


def get_sample_item_usecase(session: SessionDep) -> SampleItemUseCase:
    return SampleItemUseCase(SampleItemRepository(session))


def get_sample_file_usecase(storage: StorageDep) -> SampleFileUseCase:
    return SampleFileUseCase(storage)


SampleItemUseCaseDep = Annotated[SampleItemUseCase, Depends(get_sample_item_usecase)]
SampleFileUseCaseDep = Annotated[SampleFileUseCase, Depends(get_sample_file_usecase)]


# ---- Xác thực (issue #8) ----------------------------------------------------


@lru_cache
def get_password_service() -> PasswordService:
    return PasswordService()


def get_token_service() -> TokenService:
    return TokenService()


def get_auth_usecase(
    session: SessionDep,
    settings: SettingsDep,
    passwords: Annotated[PasswordService, Depends(get_password_service)],
    tokens: Annotated[TokenService, Depends(get_token_service)],
) -> AuthUseCase:
    return AuthUseCase(
        users=UserRepository(session),
        sessions=SessionRepository(session),
        passwords=passwords,
        tokens=tokens,
        session_ttl_hours=settings.session_ttl_hours,
    )


AuthUseCaseDep = Annotated[AuthUseCase, Depends(get_auth_usecase)]


def get_student_auth(
    session: SessionDep,
    settings: SettingsDep,
    auth: AuthUseCaseDep,
    emails: EmailServiceDep,
    tokens: Annotated[TokenService, Depends(get_token_service)],
) -> StudentAuthUseCase:
    return StudentAuthUseCase(
        auth, AuthChallengeRepository(session), emails, tokens, settings.auth_otp_secret.get_secret_value()
    )


StudentAuthDep = Annotated[StudentAuthUseCase, Depends(get_student_auth)]


def get_admin_accounts_usecase(
    session: SessionDep,
    auth: AuthUseCaseDep,
    passwords: Annotated[PasswordService, Depends(get_password_service)],
) -> AdminAccountsUseCase:
    return AdminAccountsUseCase(
        auth=auth, users=UserRepository(session), sessions=SessionRepository(session), passwords=passwords
    )


AdminAccountsUseCaseDep = Annotated[AdminAccountsUseCase, Depends(get_admin_accounts_usecase)]

# auto_error=False: thiếu header không báo lỗi ở đây; cookie vẫn được xét. Hiện nút Authorize trong Swagger.
_bearer = HTTPBearer(auto_error=False, description="Token phiên (dùng cho curl/Swagger). Cookie được ưu tiên.")


def get_session_token(
    request: Request,
    settings: SettingsDep,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str | None:
    """Lấy token: cookie trước, không có thì header Authorization: Bearer."""
    cookie = request.cookies.get(settings.cookie_name)
    if cookie:
        return cookie
    if bearer is not None and bearer.credentials:
        return bearer.credentials
    return None


async def get_current_user(
    usecase: AuthUseCaseDep,
    token: Annotated[str | None, Depends(get_session_token)],
) -> CurrentUser:
    """Phụ thuộc cho mọi endpoint cần đăng nhập. 401 khi thiếu/hết hạn/thu hồi phiên, 403 khi tài khoản bị khóa."""
    try:
        return await usecase.get_current_user(token)
    except AuthError as e:
        raise to_api_error(e, in_session_check=True) from None


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_role(*roles: str):
    """Phụ thuộc kiểm vai trò, vd `Depends(require_role("admin"))`. Sai vai trò: 403 FORBIDDEN_ROLE."""

    async def _require(current: CurrentUserDep) -> CurrentUser:
        try:
            return ensure_role(current, *roles)
        except AuthError as e:
            raise to_api_error(e) from None

    return _require


AdminDep = Annotated[CurrentUser, Depends(require_role("admin"))]
StudentDep = Annotated[CurrentUser, Depends(require_role("student"))]
