from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.repositories.exam_chat_repository import ExamChatRepository
from app.repositories.question_bank_repository import QuestionBankRepository
from app.repositories.sample_item_repository import SampleItemRepository
from app.service.exam_chat_sources import (
    ExamTemplateSource,
    NoHistory,
    NoTemplates,
    PlainReplyWriter,
    ReplyWriter,
    StudentHistorySource,
)
from app.service.storage_service import StorageService
from app.usecase.exam_chat import ExamChatUseCase
from app.usecase.sample_files import SampleFileUseCase
from app.usecase.sample_items import SampleItemUseCase

SessionDep = Annotated[AsyncSession, Depends(get_session)]


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


# ---------- issue #4: pipeline học sinh tạo đề ôn ----------
# Ba nguồn dưới đây là chỗ cắm khi các phần phụ thuộc sẵn sàng (lịch sử làm bài, mẫu đề #5, model thật).


def get_student_history() -> StudentHistorySource:
    return NoHistory()


def get_exam_template_source() -> ExamTemplateSource:
    return NoTemplates()


def get_reply_writer() -> ReplyWriter:
    return PlainReplyWriter()


def get_question_bank(session: SessionDep) -> QuestionBankRepository:
    return QuestionBankRepository(session)


def get_exam_chat_usecase(
    session: SessionDep,
    bank: Annotated[QuestionBankRepository, Depends(get_question_bank)],
    history: Annotated[StudentHistorySource, Depends(get_student_history)],
    templates: Annotated[ExamTemplateSource, Depends(get_exam_template_source)],
) -> ExamChatUseCase:
    return ExamChatUseCase(ExamChatRepository(session), bank, history, templates)


ExamChatUseCaseDep = Annotated[ExamChatUseCase, Depends(get_exam_chat_usecase)]
ReplyWriterDep = Annotated[ReplyWriter, Depends(get_reply_writer)]
