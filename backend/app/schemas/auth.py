from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _strip_email(v: Any) -> Any:
    return v.strip() if isinstance(v, str) else v


class RegisterIn(BaseModel):
    """Trường lạ (vd `role`) bị bỏ qua: đăng ký công khai luôn tạo student."""

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)

    _strip = field_validator("email", mode="before")(_strip_email)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()

    @field_validator("display_name")
    @classmethod
    def _clean_name(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None


class LoginIn(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=1, max_length=128)

    _strip = field_validator("email", mode="before")(_strip_email)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class UserOut(BaseModel):
    """Không bao giờ chứa password_hash hay token."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    role: str
    status: str
    display_name: str | None
    created_at: datetime


class ErrorOut(BaseModel):
    detail: str
    code: str


class AdminPingOut(BaseModel):
    status: str
    user_id: int
    role: str
