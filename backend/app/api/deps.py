from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.errors import to_api_error
from app.core.config import Settings, get_settings
from app.core.database import get_session, get_sessionmaker
from app.repositories.pdf_imports import PdfImportRepository
from app.repositories.sample_item_repository import SampleItemRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.service.password_service import PasswordService
from app.service.pdf_import_models import PdfImportModels
from app.service.storage_service import StorageService
from app.service.token_service import TokenService
from app.usecase.auth import AuthError, AuthUseCase, CurrentUser, ensure_role
from app.usecase.pdf_imports import PdfImportUseCase
from app.usecase.sample_files import SampleFileUseCase
from app.usecase.sample_items import SampleItemUseCase

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def get_storage() -> StorageService:
    return StorageService(get_settings())


StorageDep = Annotated[StorageService, Depends(get_storage)]


def get_sample_item_usecase(session: SessionDep) -> SampleItemUseCase:
    return SampleItemUseCase(SampleItemRepository(session))


def get_sample_file_usecase(storage: StorageDep) -> SampleFileUseCase:
    return SampleFileUseCase(storage)


SampleItemUseCaseDep = Annotated[SampleItemUseCase, Depends(get_sample_item_usecase)]
SampleFileUseCaseDep = Annotated[SampleFileUseCase, Depends(get_sample_file_usecase)]


@lru_cache
def get_pdf_import_models() -> PdfImportModels:
    return PdfImportModels(get_settings())


def get_pdf_import_usecase(
    session: SessionDep, storage: StorageDep,
    models: Annotated[PdfImportModels, Depends(get_pdf_import_models)],
) -> PdfImportUseCase:
    return PdfImportUseCase(PdfImportRepository(session), storage, models, get_settings().s3_bucket)


def get_pdf_import_runner(
    storage: StorageDep,
    models: Annotated[PdfImportModels, Depends(get_pdf_import_models)],
    sessions: Annotated[async_sessionmaker[AsyncSession], Depends(get_sessionmaker)],
):
    async def run(import_id: int) -> None:
        async with sessions() as session:
            usecase = PdfImportUseCase(PdfImportRepository(session), storage, models, get_settings().s3_bucket)
            await usecase.process(import_id)

    return run


PdfImportUseCaseDep = Annotated[PdfImportUseCase, Depends(get_pdf_import_usecase)]
PdfImportRunnerDep = Annotated[Callable[[int], Awaitable[None]], Depends(get_pdf_import_runner)]


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
