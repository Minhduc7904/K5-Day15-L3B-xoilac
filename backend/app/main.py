from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import ApiError, api_error_handler
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.usecase.pdf_imports import ImportErrorDetail


async def pdf_import_error(_: Request, exc: ImportErrorDetail) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"detail": str(exc)})


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
    app.add_exception_handler(ImportErrorDetail, pdf_import_error)
    return app


app = create_app()
