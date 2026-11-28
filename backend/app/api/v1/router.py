from fastapi import APIRouter

from app.api.v1 import (
    admin,
    admin_chapters,
    admin_questions,
    admin_stats,
    admin_users,
    admin_import,
    auth,
    exam_attempts,
    exam_chat,
    exam_templates,
    google_auth,
    health,
    notifications,
    sample_files,
    sample_items,
    student_profile,
    study_dashboard,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(student_profile.router)
api_router.include_router(notifications.router)
api_router.include_router(google_auth.router)
api_router.include_router(admin.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_stats.router)
api_router.include_router(admin_questions.router)
api_router.include_router(admin_chapters.router)
api_router.include_router(sample_items.router)
api_router.include_router(sample_files.router)
api_router.include_router(admin_import.router)
api_router.include_router(exam_templates.router)
api_router.include_router(exam_chat.router)
api_router.include_router(exam_attempts.router)
api_router.include_router(study_dashboard.router)
