from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.usecase.pdf_imports import ImportErrorDetail


async def pdf_import_error(_: Request, exc: ImportErrorDetail) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"detail": str(exc)})


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Examind API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    app.add_exception_handler(ImportErrorDetail, pdf_import_error)
    return app


app = create_app()
