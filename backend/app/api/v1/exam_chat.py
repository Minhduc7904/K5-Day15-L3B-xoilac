"""API pipeline học sinh tạo đề ôn (issue #4): phiên chat, gửi tin nhận SSE, bản xem trước, xác nhận, đề nháp.

Quyền (Auth #8): mọi route cần đăng nhập vai trò học sinh (RequesterDep lấy từ StudentDep): chưa đăng nhập 401,
không phải học sinh 403. Học sinh chỉ thấy phiên của chính mình, kể cả kết nối SSE; phiên của người khác trả 404
như không tồn tại. student_ref lấy từ tài khoản, giá trị client gửi bị bỏ qua.
"""
import json
import logging
from collections.abc import Iterator
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response, StreamingResponse

from app.api.deps import ExamChatUseCaseDep, ReplyWriterDep, RequesterDep, StorageDep
from app.repositories.credits import InsufficientCredits
from app.service.exam_chat_model import ExamChatModelError
from app.service.exam_chat_ocr import ExamChatImageError, MAX_CHAT_IMAGE_BYTES, MAX_CHAT_IMAGES
from app.usecase.live_exam_chat import LiveExamChat
from app.schemas.exam_chat import (
    ConfirmIn,
    ConfirmOut,
    DraftOut,
    MessageIn,
    MessageOut,
    PreviewOut,
    PreviewUpdate,
    SessionCreate,
    SessionOut,
    SessionListItem,
    SessionRename,
    SessionStateOut,
)
from app.usecase.exam_chat import (
    InvalidState,
    MissingStudent,
    PreviewNotFound,
    SessionNotFound,
    VersionConflict,
)
from app.usecase.exam_preview_rules import PreviewRuleError
from app.usecase.exam_template_plan import TemplateConflict

router = APIRouter(prefix="/exam-chat", tags=["exam-chat"])
log = logging.getLogger(__name__)

NO_SESSION = "Không có phiên chat này"
NO_PREVIEW = "Phiên chưa có bản xem trước"


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _not_found(message: str = NO_SESSION) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, message)


def _conflict(e: VersionConflict) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, {"message": str(e), "current_version": e.current})


def _invalid(e: PreviewRuleError) -> HTTPException:
    if isinstance(e, TemplateConflict):
        return HTTPException(422, {"message": "Chỉnh sửa xung đột với ràng buộc của mẫu kỳ thi",
                                   "code": "TEMPLATE_CONFLICT", "errors": e.errors})
    return HTTPException(422, {"message": "Cấu trúc không hợp lệ", "code": "INVALID_STRUCTURE", "errors": e.errors})


@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, usecase: ExamChatUseCaseDep, requester: RequesterDep):
    try:
        return await usecase.create_session(body.student_ref, requester)
    except MissingStudent:
        raise HTTPException(422, {"message": "Thiếu student_ref (chưa đăng nhập)"}) from None


@router.get("/sessions", response_model=list[SessionListItem])
async def list_sessions(usecase: ExamChatUseCaseDep, requester: RequesterDep):
    rows = await usecase.list_sessions(_student(requester))
    return [{**SessionOut.model_validate(session).model_dump(), "title": (session.title or title or ("Ảnh đã gửi" if title is not None else "Đoạn chat mới"))[:80]}
            for session, title in rows]


@router.patch("/sessions/{session_id}", response_model=SessionListItem)
async def rename_session(session_id: int, body: SessionRename, usecase: ExamChatUseCaseDep, requester: RequesterDep):
    try:
        item = await usecase.rename_session(session_id, _student(requester), body.title)
    except SessionNotFound:
        raise _not_found() from None
    return {**SessionOut.model_validate(item).model_dump(), "title": item.title}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: int, usecase: ExamChatUseCaseDep, requester: RequesterDep):
    """Ẩn đoạn chat khỏi danh sách. Đề nháp đã dựng vẫn còn trong "Đề của tôi"."""
    try:
        await usecase.delete_session(session_id, _student(requester))
    except SessionNotFound:
        raise _not_found() from None


@router.get("/sessions/{session_id}/transcript", response_model=list[MessageOut])
async def transcript(
    session_id: int, usecase: ExamChatUseCaseDep, requester: RequesterDep,
    before: int | None = Query(None, ge=1), limit: int = Query(80, ge=1, le=200),
):
    try:
        return await usecase.message_page(session_id, _student(requester), before, limit)
    except SessionNotFound:
        raise _not_found() from None


@router.get("/sessions/{session_id}", response_model=SessionStateOut)
async def get_session(session_id: int, usecase: ExamChatUseCaseDep, requester: RequesterDep):
    try:
        session, messages, preview, draft = await usecase.get_state(session_id, requester)
    except SessionNotFound:
        raise _not_found() from None
    return {
        "session": session,
        "messages": [MessageOut.model_validate(m) for m in messages],
        "preview": PreviewOut.model_validate(preview) if preview and preview.status != "CANCELLED" else None,
        "draft": DraftOut.model_validate(draft) if draft else None,
    }


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: int, body: MessageIn, usecase: ExamChatUseCaseDep, writer: ReplyWriterDep, requester: RequesterDep
):
    """Gửi một tin nhắn văn bản, nhận phản hồi qua SSE."""
    return await _send_message(session_id, body.text, body.version, usecase, writer, requester, plan=body.plan)


@router.post("/sessions/{session_id}/messages/with-images")
async def send_images(
    session_id: int, usecase: ExamChatUseCaseDep, writer: ReplyWriterDep, requester: RequesterDep,
    images: Annotated[list[UploadFile], File(min_length=1, max_length=MAX_CHAT_IMAGES)],
    text: Annotated[str, Form(max_length=2000)] = "",
    version: Annotated[int | None, Form(ge=0)] = None,
    image_purpose: Annotated[Literal["matrix", "topic"] | None, Form()] = None,
):
    """Gửi ảnh ma trận đề hoặc ảnh bài/dạng cần ôn, kèm tin nhắn. Phản hồi dùng cùng SSE với tin nhắn văn bản."""
    if not isinstance(usecase, LiveExamChat):
        raise HTTPException(503, {"code": "EXAM_CHAT_UNAVAILABLE", "message": "Chat có ảnh chưa được bật."})
    await _check_owner(usecase, requester, session_id)
    remaining = MAX_CHAT_IMAGE_BYTES
    blobs = []
    for upload in images:
        data = await upload.read(remaining + 1)
        remaining -= len(data)
        if remaining < 0:
            raise HTTPException(413, {"code": "IMAGES_TOO_LARGE", "message": "Tổng dung lượng ảnh tối đa 4 MB."})
        blobs.append(data)
    return await _send_message(session_id, text.strip(), version, usecase, writer, requester, blobs,
                               image_purpose=image_purpose)


async def _check_owner(usecase, requester, session_id):
    try:
        await usecase.check_owner(session_id, _student(requester))
    except SessionNotFound:
        raise _not_found() from None


async def _send_message(session_id, text, version, usecase, writer, requester, images=None, plan=None,
                        image_purpose=None):
    try:
        if isinstance(usecase, LiveExamChat):
            turn = await usecase.respond(session_id, text, requester, version=version, images=images, plan=plan,
                                         image_purpose=image_purpose)
        else:
            turn = await usecase.respond(session_id, text, requester)
    except SessionNotFound:  # kiểm quyền trước khi mở luồng: phiên của người khác trả 404 thường
        raise _not_found() from None
    except VersionConflict as e:
        raise _conflict(e) from e
    except InsufficientCredits as e:
        raise HTTPException(402, {"code": "INSUFFICIENT_CREDITS", "message": "Cần 100 credit để tạo đề đầu tiên."}) from e
    except ExamChatImageError as e:
        raise HTTPException(e.status, {"code": e.code, "message": str(e)}) from e
    except ExamChatModelError as e:
        log.warning("exam-chat model unavailable: %s", e)
        raise HTTPException(503, {"code": "EXAM_CHAT_UNAVAILABLE", "message": "Agent đang bận. Em thử lại nhé."}) from e
    except Exception:  # lỗi không lường trước: báo qua SSE thay vì cắt kết nối
        log.exception("exam-chat respond failed")

        def failed() -> Iterator[str]:
            yield _sse("error", {"code": "internal_error", "message": "Có lỗi khi xử lý tin nhắn, em thử lại nhé."})

        return StreamingResponse(failed(), media_type="text/event-stream")

    def events() -> Iterator[str]:
        for chunk in writer.stream(turn.reply):
            yield _sse("message", {"delta": chunk})
        if turn.preview_changed:
            yield _sse("preview", PreviewOut.model_validate(turn.preview).model_dump(mode="json") if turn.preview else None)
        if turn.draft is not None:
            yield _sse("draft", DraftOut.model_validate(turn.draft).model_dump(mode="json"))
        yield _sse("done", {"preview_version": turn.preview.version if turn.preview else None})

    return StreamingResponse(
        events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.get("/sessions/{session_id}/attachments/{attachment_id}")
async def get_chat_attachment(
    session_id: int, attachment_id: int, usecase: ExamChatUseCaseDep, requester: RequesterDep, storage: StorageDep,
):
    try:
        data, mime = await usecase.chat_attachment(session_id, _student(requester), attachment_id, storage)
    except SessionNotFound:
        raise _not_found("Không tìm thấy ảnh") from None
    return Response(data, media_type=mime, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/sessions/{session_id}/preview", response_model=PreviewOut)
async def get_preview(session_id: int, usecase: ExamChatUseCaseDep, requester: RequesterDep):
    try:
        preview = await usecase.get_preview(session_id, requester)
        if preview.status == "CANCELLED":
            raise PreviewNotFound()
        return preview
    except SessionNotFound:
        raise _not_found() from None
    except PreviewNotFound:
        raise _not_found(NO_PREVIEW) from None


@router.patch("/sessions/{session_id}/preview", response_model=PreviewOut)
async def update_preview(session_id: int, body: PreviewUpdate, usecase: ExamChatUseCaseDep, requester: RequesterDep):
    try:
        return await usecase.update_preview(session_id, body.edit, body.version, requester)
    except SessionNotFound:
        raise _not_found() from None
    except PreviewNotFound:
        raise _not_found(NO_PREVIEW) from None
    except VersionConflict as e:
        raise _conflict(e) from e
    except PreviewRuleError as e:
        raise _invalid(e) from e


@router.post("/sessions/{session_id}/preview/confirm", response_model=ConfirmOut)
async def confirm_preview(session_id: int, body: ConfirmIn, usecase: ExamChatUseCaseDep, requester: RequesterDep):
    """Xác nhận bản xem trước rồi dựng đề nháp từ câu đã duyệt."""
    try:
        if isinstance(usecase, LiveExamChat):
            preview, draft, message = await usecase.confirm(session_id, body.version, requester, accepted_count=body.accepted_count)
        else:
            preview, draft, message = await usecase.confirm(session_id, body.version, requester)
    except SessionNotFound:
        raise _not_found() from None
    except PreviewNotFound:
        raise _not_found(NO_PREVIEW) from None
    except VersionConflict as e:
        raise _conflict(e) from e
    except InsufficientCredits as e:
        raise HTTPException(402, {"code": "INSUFFICIENT_CREDITS", "message": "Cần 100 credit để tạo đề đầu tiên."}) from e
    except InvalidState as e:
        raise HTTPException(status.HTTP_409_CONFLICT, {"message": str(e)}) from e
    except PreviewRuleError as e:
        raise _invalid(e) from e
    return {"preview": preview, "draft": draft, "message": message}


@router.get("/sessions/{session_id}/draft", response_model=DraftOut)
async def get_draft(session_id: int, usecase: ExamChatUseCaseDep, requester: RequesterDep):
    try:
        draft = await usecase.latest_draft(session_id, requester)
    except SessionNotFound:
        raise _not_found() from None
    if draft is None:
        raise _not_found("Phiên chưa có đề nháp")
    return draft


def _student(requester):
    if requester is None:
        raise HTTPException(401)
    return requester


@router.get("/drafts", response_model=list[DraftOut])
async def list_drafts(usecase: ExamChatUseCaseDep, requester: RequesterDep):
    return await usecase.list_drafts(_student(requester))


@router.get("/drafts/{draft_id}", response_model=DraftOut)
async def get_draft_by_id(draft_id: int, usecase: ExamChatUseCaseDep, requester: RequesterDep):
    try:
        return await usecase.draft_by_id(_student(requester), draft_id)
    except SessionNotFound:
        raise _not_found("Không tìm thấy đề nháp") from None


@router.get("/drafts/{draft_id}/media/{media_id}")
async def get_draft_media(
    draft_id: int, media_id: int, usecase: ExamChatUseCaseDep, requester: RequesterDep, storage: StorageDep,
):
    try:
        data, mime = await usecase.draft_media(_student(requester), draft_id, media_id, storage)
    except SessionNotFound:
        raise _not_found("Không tìm thấy ảnh") from None
    return Response(data, media_type=mime, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/chapters")
async def get_chapters(usecase: ExamChatUseCaseDep, requester: RequesterDep):
    _student(requester)
    return await usecase.chapter_catalog()
