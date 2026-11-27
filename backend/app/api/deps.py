from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database import get_session, get_sessionmaker
from app.repositories.pdf_imports import PdfImportRepository
from app.repositories.sample_item_repository import SampleItemRepository
from app.service.storage_service import StorageService
from app.service.pdf_import_models import PdfImportModels
from app.usecase.pdf_imports import PdfImportUseCase
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
