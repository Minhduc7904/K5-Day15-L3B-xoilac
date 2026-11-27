import uuid

from app.schemas.sample import SampleFileOut
from app.service.storage_service import StorageService

MAX_BYTES = 5 * 1024 * 1024


class FileTooLarge(Exception):
    pass


class SampleFileUseCase:
    def __init__(self, storage: StorageService) -> None:
        self._storage = storage

    async def upload(self, data: bytes, content_type: str) -> SampleFileOut:
        if len(data) > MAX_BYTES:
            raise FileTooLarge()
        key = f"samples/{uuid.uuid4().hex}"
        await self._storage.put(key, data, content_type)
        return SampleFileOut(key=key, size=len(data), content_type=content_type)

    async def download(self, key: str) -> tuple[bytes, str] | None:
        return await self._storage.get(key)
