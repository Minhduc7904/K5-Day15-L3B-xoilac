from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.usecase.auth import PASSWORD_MAX, PASSWORD_MIN

Role = Literal["student", "admin"]
Status = Literal["active", "disabled"]


def _strip_lower_email(v: object) -> object:
    return v.strip().lower() if isinstance(v, str) else v


def _clean_name(v: str | None) -> str | None:
    v = v.strip() if v else None
    return v or None


class UserAdminOut(BaseModel):
    """Không bao giờ chứa password_hash hay token."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    display_name: str | None
    role: str
    status: str
    is_root: bool
    created_at: datetime
    created_by: int | None
    last_login_at: datetime | None


class UserListOut(BaseModel):
    items: list[UserAdminOut]
    total: int
    page: int
    page_size: int


class UserCreateIn(BaseModel):
    # extra="forbid": gửi is_root (hay trường lạ) thì 422, không âm thầm bỏ qua.
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    role: Role = "student"
    display_name: str | None = Field(default=None, max_length=100)

    _email = field_validator("email", mode="before")(_strip_lower_email)
    _name = field_validator("display_name")(_clean_name)


class UserUpdateIn(BaseModel):
    """Chỉ các trường gửi lên mới được đổi. is_root không có ở đây: không ai đặt được qua API."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = Field(default=None, max_length=255)
    role: Role | None = None
    status: Status | None = None

    _email = field_validator("email", mode="before")(_strip_lower_email)
    _name = field_validator("display_name")(_clean_name)

    def changes(self) -> dict:
        """Các trường client gửi lên. display_name gửi null/rỗng nghĩa là xoá tên; các trường khác không nhận null."""
        data = self.model_dump(exclude_unset=True)
        return {k: v for k, v in data.items() if v is not None or k == "display_name"}


class ResetPasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
