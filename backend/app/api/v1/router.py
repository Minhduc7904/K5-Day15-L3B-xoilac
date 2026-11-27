from fastapi import APIRouter

from app.api.v1 import admin_import, health, sample_files, sample_items

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(sample_items.router)
api_router.include_router(sample_files.router)
api_router.include_router(admin_import.router)
