from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StrictBool, model_validator

Answer = Annotated[str, Field(max_length=2000)] | Annotated[list[StrictBool | None], Field(max_length=4)] | None


class AttemptStart(BaseModel):
    restart: bool = False


class AttemptSave(BaseModel):
    mutation_id: UUID
    question: str = Field(max_length=32)
    answer: Answer = None
    base_revision: int | None = Field(default=None, ge=0)
    tab_id: UUID | None = None
    elapsed_ms: int = Field(default=0, ge=0, le=6000)
    current: str | None = Field(default=None, max_length=32)
    release_tab: bool = False

    @model_validator(mode="after")
    def validate_operation(self):
        if self.base_revision is None and self.tab_id is None:
            raise ValueError("Thao tác cần phiên bản đáp án hoặc thông tin thời gian.")
        return self
