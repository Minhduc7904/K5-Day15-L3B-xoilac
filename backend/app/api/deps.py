from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.errors import to_api_error
from app.core.config import Settings, get_settings
from app.core.database import get_session, get_sessionmaker
from app.repositories.admin_question_repository import AdminQuestionRepository
from app.repositories.auth_challenge_repository import AuthChallengeRepository
from app.repositories.credits import CreditRepository
from app.repositories.student_profiles import StudentProfileRepository
from app.repositories.exam_attempts import ExamAttemptRepository
from app.repositories.exam_chat_repository import ExamChatRepository
from app.repositories.exam_template_repository import ExamTemplateRepository
from app.repositories.notifications import NotificationRepository
from app.repositories.pdf_imports import PdfImportRepository
from app.repositories.question_bank_repository import QuestionBankRepository
from app.repositories.sample_item_repository import SampleItemRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.service.exam_chat_sources import (
    ExamTemplateSource,
    PlainReplyWriter,
    ReplyWriter,
    StudentHistorySource,
    TemplateLookupSource,
)
from app.service.email_service import GmailEmailService
from app.service.google_identity import GoogleIdentityService
from app.service.password_service import PasswordService
from app.service.pdf_import_models import PdfImportModels
from app.service.storage_service import StorageService
from app.service.token_service import TokenService
from app.usecase.admin_questions import AdminQuestionUseCase
from app.usecase.auth import AuthError, AuthUseCase, CurrentUser, ensure_role
from app.usecase.exam_chat import ExamChatUseCase, Requester
from app.usecase.live_exam_chat import LiveExamChat
from app.service.exam_chat_model import ExamChatModel
from app.service.exam_chat_ocr import ExamChatOcr
from app.usecase.exam_templates import ExamTemplateUseCase
from app.usecase.notifications import Notifications
from app.usecase.online_stats import OnlineStatsUseCase
from app.usecase.pdf_imports import PdfImportUseCase
from app.usecase.sample_files import SampleFileUseCase
from app.usecase.sample_items import SampleItemUseCase
from app.usecase.student_auth import StudentAuthUseCase
from app.usecase.student_profile import StudentProfileUseCase
from app.usecase.study_dashboard import AttemptHistory, StudyDashboard
from app.usecase.user_management import UserManagementUseCase

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


def get_exam_template_usecase(session: SessionDep) -> ExamTemplateUseCase:
    return ExamTemplateUseCase(ExamTemplateRepository(session))


SampleItemUseCaseDep = Annotated[SampleItemUseCase, Depends(get_sample_item_usecase)]
SampleFileUseCaseDep = Annotated[SampleFileUseCase, Depends(get_sample_file_usecase)]
ExamTemplateUseCaseDep = Annotated[ExamTemplateUseCase, Depends(get_exam_template_usecase)]


# ---- Xác thực (issue #8) ----------------------------------------------------


@lru_cache
def get_password_service() -> PasswordService:
    return PasswordService()


def get_token_service() -> TokenService:
    return TokenService()


def get_auth_usecase(
    request: Request,
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
        realtime=request.app.state.realtime,
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
        auth,
        AuthChallengeRepository(session),
        emails,
        tokens,
        settings.auth_otp_secret.get_secret_value(),
        settings.frontend_url,
    )


StudentAuthDep = Annotated[StudentAuthUseCase, Depends(get_student_auth)]


def get_user_management_usecase(
    request: Request,
    session: SessionDep,
    auth: AuthUseCaseDep,
    passwords: Annotated[PasswordService, Depends(get_password_service)],
) -> UserManagementUseCase:
    """#20: notifier là RealtimeServer của app (revoke_user ngắt mọi socket của người bị khoá)."""
    return UserManagementUseCase(
        auth=auth,
        users=UserRepository(session),
        sessions=SessionRepository(session),
        passwords=passwords,
        notifier=request.app.state.realtime,
    )


UserManagementUseCaseDep = Annotated[UserManagementUseCase, Depends(get_user_management_usecase)]


def get_online_stats_usecase(request: Request, session: SessionDep) -> OnlineStatsUseCase:
    """#20: đọc PresenceRegistry của RealtimeServer (một tiến trình, trong bộ nhớ)."""
    return OnlineStatsUseCase(presence=request.app.state.realtime.presence, users=UserRepository(session))


OnlineStatsUseCaseDep = Annotated[OnlineStatsUseCase, Depends(get_online_stats_usecase)]


def get_admin_question_usecase(session: SessionDep, storage: StorageDep, settings: SettingsDep) -> AdminQuestionUseCase:
    """#11: ngân hàng câu hỏi cho admin; ảnh lưu MinIO qua StorageService."""
    return AdminQuestionUseCase(AdminQuestionRepository(session), storage, settings.s3_bucket)


AdminQuestionUseCaseDep = Annotated[AdminQuestionUseCase, Depends(get_admin_question_usecase)]

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


def get_student_profile(session: SessionDep) -> StudentProfileUseCase:
    return StudentProfileUseCase(StudentProfileRepository(session), CreditRepository(session))


StudentProfileDep = Annotated[StudentProfileUseCase, Depends(get_student_profile)]


def get_notifications(session: SessionDep) -> Notifications:
    return Notifications(NotificationRepository(session))


NotificationsDep = Annotated[Notifications, Depends(get_notifications)]


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


# ---------- issue #4: pipeline học sinh tạo đề ôn ----------


def get_requester(current: StudentDep) -> Requester:
    """Học sinh đang đăng nhập. Mọi route /exam-chat cần vai trò học sinh và chỉ thấy phiên của chính mình (kể cả SSE).

    student_ref tra lịch sử được tạo từ user_id của phiên đã xác thực.
    """
    return Requester(user_id=current.user_id, student_ref=f"U{current.user_id}")


def get_study_dashboard(session: SessionDep) -> StudyDashboard:
    return StudyDashboard(ExamAttemptRepository(session), QuestionBankRepository(session))


StudentDashboardDep = Annotated[StudyDashboard, Depends(get_study_dashboard)]


def get_student_history(dashboard: StudentDashboardDep) -> StudentHistorySource:
    """Lịch sử làm bài thật từ các lượt đã chấm. Chưa có lượt nào thì agent nói chưa có lịch sử và hỏi chương."""
    return AttemptHistory(dashboard)


def get_exam_template_source(templates: ExamTemplateUseCaseDep) -> ExamTemplateSource:
    """Nhánh ôn theo mẫu kỳ thi đọc mẫu ĐÃ DUYỆT qua hợp đồng tra cứu của #5."""
    return TemplateLookupSource(templates.lookup)


def get_reply_writer() -> ReplyWriter:
    """Chưa chốt model và key: trả văn bản dựng bằng code, chia theo dòng để phát qua SSE."""
    return PlainReplyWriter()


def get_question_bank(session: SessionDep) -> QuestionBankRepository:
    return QuestionBankRepository(session)


def get_exam_chat_usecase(
    session: SessionDep,
    bank: Annotated[QuestionBankRepository, Depends(get_question_bank)],
    history: Annotated[StudentHistorySource, Depends(get_student_history)],
    templates: Annotated[ExamTemplateSource, Depends(get_exam_template_source)],
    ocr_models: Annotated[PdfImportModels, Depends(get_pdf_import_models)],
    storage: StorageDep,
) -> ExamChatUseCase:
    args = (ExamChatRepository(session), bank, history, templates)
    settings = get_settings()
    if settings.exam_chat_live:
        return LiveExamChat(session, ExamChatModel(settings), ExamChatOcr(ocr_models), storage, *args)
    return ExamChatUseCase(*args)


ExamChatUseCaseDep = Annotated[ExamChatUseCase, Depends(get_exam_chat_usecase)]
ReplyWriterDep = Annotated[ReplyWriter, Depends(get_reply_writer)]
RequesterDep = Annotated[Requester | None, Depends(get_requester)]
