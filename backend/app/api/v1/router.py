from fastapi import APIRouter

from app.api.v1 import admin, admin_users, auth, health, sample_files, sample_items

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(admin_users.router)
api_router.include_router(sample_items.router)
api_router.include_router(sample_files.router)
