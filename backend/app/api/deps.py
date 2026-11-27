from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.repositories.sample_item_repository import SampleItemRepository
from app.service.storage_service import StorageService
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
