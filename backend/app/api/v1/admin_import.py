import hmac
import time
from secrets import token_bytes
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, UploadFile
from app.api.deps import PdfImportRunnerDep, PdfImportUseCaseDep, require_role
from app.models.pdf_import import PdfDraft, PdfImport
from app.schemas.pdf_import import DraftEdit
from app.usecase.pdf_imports import MAX_PDF_BYTES

router = APIRouter(prefix="/admin/pdf-imports", tags=["pdf-import"])
MEDIA_TTL_SECONDS = 300
MEDIA_SIGNING_KEY = token_bytes(32)
require_admin = require_role("admin")


def import_response(row: PdfImport, request: Request) -> dict:
    return {
        "id": row.id, "filename": row.filename, "status": row.status, "stage": row.stage,
        "pageCount": row.page_count, "originalMediaId": row.original_media_id, "error": row.error,
        "warnings": row.warnings, "ocrModel": row.ocr_model, "extractionModel": row.extraction_model,
        "createdAt": row.created_at,
        "statusUrl": str(request.app.url_path_for("get_pdf_import", import_id=row.id)),
    }


def draft_response(row: PdfDraft) -> dict:
    return {**row.payload, "id": row.id, "position": row.position, "status": row.status, "questionId": row.question_id}


def media_signature(import_id: int, media_id: int, exp: int) -> str:
    return hmac.digest(MEDIA_SIGNING_KEY, f"pdf-media:{import_id}:{media_id}:{exp}".encode(), "sha256").hex()


@router.post("", status_code=202, dependencies=[Depends(require_admin)])
async def upload_pdf(
    file: UploadFile, request: Request, tasks: BackgroundTasks, usecase: PdfImportUseCaseDep,
    run_import: PdfImportRunnerDep,
):
    if not usecase.providers_configured:
        raise HTTPException(503, "Chưa cấu hình OCR hoặc model tách đề.")
    row = await usecase.upload(file.filename or "exam.pdf", await file.read(MAX_PDF_BYTES + 1))
    tasks.add_task(run_import, row.id)
    return import_response(row, request)


@router.get("", dependencies=[Depends(require_admin)])
async def list_pdf_imports(
    request: Request, usecase: PdfImportUseCaseDep, offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
):
    return [import_response(row, request) for row in await usecase.list_imports(offset, limit)]


@router.get("/{import_id}", dependencies=[Depends(require_admin)])
async def get_pdf_import(import_id: int, request: Request, usecase: PdfImportUseCaseDep):
    row = await usecase.get_import(import_id)
    return {**import_response(row, request), "draftCount": len(await usecase.list_drafts(import_id))}


@router.get("/{import_id}/drafts", dependencies=[Depends(require_admin)])
async def list_drafts(import_id: int, usecase: PdfImportUseCaseDep):
    return [draft_response(draft) for draft in await usecase.list_drafts(import_id)]


@router.get("/{import_id}/drafts/{draft_id}", dependencies=[Depends(require_admin)])
async def get_draft(import_id: int, draft_id: int, usecase: PdfImportUseCaseDep):
    return draft_response(await usecase.get_draft(import_id, draft_id))


@router.patch("/{import_id}/drafts/{draft_id}", dependencies=[Depends(require_admin)])
async def edit_draft(import_id: int, draft_id: int, edit: DraftEdit, usecase: PdfImportUseCaseDep):
    return draft_response(await usecase.edit(import_id, draft_id, edit))


@router.post("/{import_id}/drafts/{draft_id}/approve", dependencies=[Depends(require_admin)])
async def approve_draft(import_id: int, draft_id: int, usecase: PdfImportUseCaseDep):
    return draft_response(await usecase.decide(import_id, draft_id, approve=True))


@router.post("/{import_id}/drafts/{draft_id}/reject", dependencies=[Depends(require_admin)])
async def reject_draft(import_id: int, draft_id: int, usecase: PdfImportUseCaseDep):
    return draft_response(await usecase.decide(import_id, draft_id, approve=False))


@router.get("/{import_id}/media/{media_id}/url", dependencies=[Depends(require_admin)])
async def get_media_url(import_id: int, media_id: int, request: Request, usecase: PdfImportUseCaseDep):
    await usecase.get_asset(import_id, media_id)
    expiry = int(time.time()) + MEDIA_TTL_SECONDS
    signature = media_signature(import_id, media_id, expiry)
    path = request.app.url_path_for("download_pdf_import_media", import_id=import_id, media_id=media_id)
    return {"url": f"{path}?expires={expiry}&signature={signature}", "expiresAt": expiry}


@router.get("/{import_id}/media/{media_id}", response_class=Response)
async def download_pdf_import_media(
    import_id: int, media_id: int, expires: int, signature: str, usecase: PdfImportUseCaseDep
):
    expected = media_signature(import_id, media_id, expires)
    if expires <= time.time() or not hmac.compare_digest(signature.encode(), expected.encode()):
        raise HTTPException(403, "URL xem tệp không hợp lệ hoặc đã hết hạn.")
    data, mime = await usecase.download(import_id, media_id)
    return Response(data, media_type=mime, headers={
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox", "Referrer-Policy": "no-referrer",
    })
