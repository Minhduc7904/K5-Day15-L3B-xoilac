from fastapi import APIRouter, Request
from sqlalchemy import text

from app.api.deps import SessionDep, StorageDep
from app.schemas.sample import HealthOut, LiveOut

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LiveOut)
async def live(request: Request) -> LiveOut:
    """Liveness: chỉ cho biết process còn sống, không chạm DB hay MinIO."""
    return LiveOut(status="ok", version=request.app.version)


@router.get("/health", response_model=HealthOut)
async def health(session: SessionDep, storage: StorageDep) -> HealthOut:
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    storage_ok = await storage.ping()
    return HealthOut(status="ok" if db_ok and storage_ok else "degraded", database=db_ok, storage=storage_ok)
