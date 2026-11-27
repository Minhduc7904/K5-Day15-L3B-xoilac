import secrets

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_storage
from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.models import Base


TEST_SETTINGS = Settings(_env_file=None, cookie_name="examind_session", cookie_secure=False, session_ttl_hours=168)


def new_password() -> str:
    """Mật khẩu ngẫu nhiên sinh lúc chạy test (19+ ký tự). Không viết cứng mật khẩu trong repo.

    Test độ dài dùng "x" * n; test sai mật khẩu gọi hàm này thêm một lần để có giá trị khác.
    """
    return "T-" + secrets.token_urlsafe(16)


@pytest.fixture
def make_password():
    """Fixture trả về hàm sinh mật khẩu: `pw = make_password()`."""
    return new_password


class FakeStorage:
    """Thay MinIO trong test: giữ tệp trong bộ nhớ."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    async def get(self, key: str):
        return self.objects.get(key)

    async def ping(self) -> bool:
        return True


@pytest.fixture
async def db():
    """Session maker trỏ vào SQLite trong bộ nhớ; test dùng để đọc/sửa DB trực tiếp."""
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def client(db):
    storage = FakeStorage()

    async def _session():
        async with db() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_storage] = lambda: storage
    # Cấu hình cố định cho test, không phụ thuộc backend/.env trên máy.
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
