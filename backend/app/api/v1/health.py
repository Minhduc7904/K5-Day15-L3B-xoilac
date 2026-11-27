from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SessionDep, StorageDep
from app.schemas.sample import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health(session: SessionDep, storage: StorageDep) -> HealthOut:
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    storage_ok = await storage.ping()
    return HealthOut(status="ok" if db_ok and storage_ok else "degraded", database=db_ok, storage=storage_ok)
