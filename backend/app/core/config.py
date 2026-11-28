from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://examind:examind@localhost:5432/examind"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "examind"
    # Rỗng: không bật CORS. Frontend gọi qua rewrites của Next.js nên cùng origin.
    cors_origins: str = ""

    # Phiên đăng nhập (issue #8)
    cookie_name: str = "examind_session"
    # Cookie riêng của admin: đăng nhập admin không đè phiên học sinh trong cùng trình duyệt.
    admin_cookie_name: str = "examind_admin_session"
    cookie_secure: bool = False
    session_ttl_hours: int = Field(default=168, ge=1)

    # Admin mặc định, chỉ lệnh `python -m app.cli.ensure_admin` đọc (chạy trong db-init).
    # SecretStr để mật khẩu không lộ khi in hay log đối tượng Settings.
    admin_email: str = ""
    admin_password: SecretStr = SecretStr("")
    admin_name: str = ""

    mistral_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    exam_chat_live: bool = False
    exam_chat_model: str = "gpt-5.4-mini"
    ocr_provider: Literal["mistral"] = "mistral"
    ocr_model: str = "mistral-ocr-4-1"
    pdf_import_extraction_model: str = "gpt-5.4-mini"
    pdf_import_embedding_model: str = "text-embedding-3-small"

    email_provider: str = ""
    email_from: str = ""
    email_from_name: str = "Examind"
    gmail_client_id: SecretStr = SecretStr("")
    gmail_client_secret: SecretStr = SecretStr("")
    gmail_refresh_token: SecretStr = SecretStr("")

    auth_otp_secret: SecretStr = SecretStr("")
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    google_callback_url: str = ""
    frontend_url: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
