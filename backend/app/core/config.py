from functools import lru_cache
from typing import Literal

from pydantic import SecretStr

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://examind:examind@localhost:5432/examind"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "examind"
    cors_origins: str = "http://localhost:3000"

    pdf_import_admin_token: SecretStr | None = None
    mistral_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    ocr_provider: Literal["mistral"] = "mistral"
    ocr_model: str = "mistral-ocr-4-1"
    pdf_import_extraction_model: str = "gpt-5.4-mini"
    pdf_import_embedding_model: str = "text-embedding-3-small"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
