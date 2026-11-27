from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class AdminAccountOut(BaseModel):
    """Không bao giờ chứa password_hash hay token."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    display_name: str | None
    status: str
    created_at: datetime
    created_by: int | None
    last_login_at: datetime | None


class AdminCreateIn(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)
    current_password: str = Field(min_length=1, max_length=128, description="Mật khẩu của admin đang thao tác")

    @field_validator("email", mode="before")
    @classmethod
    def _strip(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()

    @field_validator("display_name")
    @classmethod
    def _clean_name(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None


class AdminStatusIn(BaseModel):
    status: Literal["active", "disabled"]
    current_password: str = Field(min_length=1, max_length=128, description="Mật khẩu của admin đang thao tác")
