import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import ApiError, api_error_handler
from app.api.realtime import RealtimeMiddleware, RealtimeServer
from app.api.v1.google_auth import callback_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import get_sessionmaker
from app.usecase.pdf_imports import ImportErrorDetail


async def pdf_import_error(_: Request, exc: ImportErrorDetail) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"detail": str(exc)})


class OAuthCallbackAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/auth/google/callback?" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(OAuthCallbackAccessFilter())


async def validation_error_handler(request: Request, error: RequestValidationError):
    if not request.url.path.startswith("/api/v1/auth/"):
        return await request_validation_exception_handler(request, error)
    details = [{key: issue[key] for key in ("type", "loc", "msg")} for issue in error.errors()]
    return JSONResponse({"detail": details}, status_code=422, headers={"Cache-Control": "no-store"})


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
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(api_router)
    app.add_exception_handler(ImportErrorDetail, pdf_import_error)
    app.include_router(callback_router)
    app.state.realtime = RealtimeServer(settings.cors_origin_list, get_sessionmaker)
    app.add_middleware(RealtimeMiddleware, realtime=app.state.realtime)
    return app


app = create_app()
