from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SampleItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class SampleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class SampleFileOut(BaseModel):
    key: str
    size: int
    content_type: str


class HealthOut(BaseModel):
    status: str
    database: bool
    storage: bool


class LiveOut(BaseModel):
    status: str
    version: str
