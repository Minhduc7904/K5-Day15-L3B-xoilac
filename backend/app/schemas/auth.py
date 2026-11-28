from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.usecase.auth import PASSWORD_MAX, PASSWORD_MIN


def _strip_email(v: Any) -> Any:
    return v.strip() if isinstance(v, str) else v


class RegisterIn(BaseModel):
    """Trường lạ (vd `role`) bị bỏ qua: đăng ký công khai luôn tạo student."""

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    display_name: str | None = Field(default=None, max_length=100)

    _strip = field_validator("email", mode="before")(_strip_email)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        if not v.rpartition("@")[0].isascii():
            raise ValueError("Email local part must use ASCII characters.")
        return v.lower()

    @field_validator("display_name")
    @classmethod
    def _clean_name(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None


OpaqueToken = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{43}$")]


class OtpChallengeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    challenge: str
    email: str
    expires_in: int
    resend_after: int


class OtpResendIn(BaseModel):
    challenge: OpaqueToken
    purpose: Literal["registration", "google_email"]


class OtpIn(OtpResendIn):
    otp: str = Field(pattern=r"^[0-9]{6}$")


class GoogleStartIn(BaseModel):
    challenge: OpaqueToken


class GoogleStartOut(BaseModel):
    url: str


class GoogleExchangeIn(BaseModel):
    ticket: OpaqueToken
    verifier: OpaqueToken


class LoginIn(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=1, max_length=128)

    _strip = field_validator("email", mode="before")(_strip_email)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class PasswordForgotIn(BaseModel):
    email: EmailStr = Field(max_length=255)

    _strip = field_validator("email", mode="before")(_strip_email)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class PasswordVerifyIn(PasswordForgotIn):
    otp: str = Field(pattern=r"^[0-9]{6}$")


class ResetTokenOut(BaseModel):
    reset_token: str


class PasswordResetIn(BaseModel):
    reset_token: OpaqueToken
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


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
