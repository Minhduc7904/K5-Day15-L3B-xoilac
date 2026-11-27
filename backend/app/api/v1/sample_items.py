from fastapi import APIRouter, HTTPException, status

from app.api.deps import SampleItemUseCaseDep
from app.schemas.sample import SampleItemCreate, SampleItemOut

router = APIRouter(prefix="/sample-items", tags=["sample"])


@router.post("", response_model=SampleItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(body: SampleItemCreate, usecase: SampleItemUseCaseDep):
    return await usecase.create(body.name)


@router.get("", response_model=list[SampleItemOut])
async def list_items(usecase: SampleItemUseCaseDep):
    return await usecase.list()


@router.get("/{item_id}", response_model=SampleItemOut)
async def get_item(item_id: int, usecase: SampleItemUseCaseDep):
    item = await usecase.get(item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không có bản ghi này")
    return item
