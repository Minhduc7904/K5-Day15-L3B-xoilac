from fastapi import APIRouter, HTTPException, Response, UploadFile, status

from app.api.deps import SampleFileUseCaseDep
from app.schemas.sample import SampleFileOut
from app.usecase.sample_files import MAX_BYTES, FileTooLarge

router = APIRouter(prefix="/sample-files", tags=["sample"])


@router.post("", response_model=SampleFileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile, usecase: SampleFileUseCaseDep):
    data = await file.read(MAX_BYTES + 1)
    try:
        return await usecase.upload(data, file.content_type or "application/octet-stream")
    except FileTooLarge:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Tệp mẫu tối đa 5 MB")


@router.get("/{key:path}")
async def download_file(key: str, usecase: SampleFileUseCaseDep):
    if not key.startswith("samples/"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không có tệp này")
    found = await usecase.download(key)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không có tệp này")
    data, content_type = found
    return Response(content=data, media_type=content_type)
