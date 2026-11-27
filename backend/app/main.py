import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import realtime_scope
from app.api.errors import ApiError, api_error_handler
from app.api.socket.server import register_handlers, sio
from app.api.v1.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Examind API", version="0.1.0")
    if settings.cors_origin_list:
        # Chỉ cho dev khi frontend khác origin. Có cookie phiên nên phải bật credentials.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(api_router)
    return app


app = create_app()

# Socket.IO (#20) gắn trước FastAPI tại /api/socket.io; mọi đường dẫn khác chuyển cho FastAPI.
# uvicorn chạy `app.main:asgi_app`. `app` (FastAPI) giữ nguyên để test dùng dependency_overrides.
register_handlers(sio, realtime_scope(app))
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="api/socket.io")
