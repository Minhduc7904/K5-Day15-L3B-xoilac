"""API pipeline học sinh tạo đề ôn (issue #4): phiên chat, gửi tin nhận SSE, bản xem trước, xác nhận, đề nháp.

Chưa có xác thực: student_ref do client gửi khi tạo phiên. Khi có Auth (#8), lấy học sinh từ phiên đăng nhập và
kiểm học sinh chỉ đọc được phiên của mình, kể cả với kết nối SSE.
"""
import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import ExamChatUseCaseDep, ReplyWriterDep
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
    SessionStateOut,
)
from app.usecase.exam_chat import InvalidState, PreviewNotFound, SessionNotFound, VersionConflict
from app.usecase.exam_preview_rules import PreviewRuleError

router = APIRouter(prefix="/exam-chat", tags=["exam-chat"])
log = logging.getLogger(__name__)

NO_SESSION = "Không có phiên chat này"
NO_PREVIEW = "Phiên chưa có bản xem trước"


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _conflict(e: VersionConflict) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, {"message": str(e), "current_version": e.current})


def _invalid(e: PreviewRuleError) -> HTTPException:
    return HTTPException(422, {"message": "Cấu trúc không hợp lệ", "errors": e.errors})


@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, usecase: ExamChatUseCaseDep):
    return await usecase.create_session(body.student_ref)


@router.get("/sessions/{session_id}", response_model=SessionStateOut)
async def get_session(session_id: int, usecase: ExamChatUseCaseDep):
    try:
        session, messages, preview, draft = await usecase.get_state(session_id)
    except SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_SESSION) from None
    return {
        "session": session,
        "messages": [MessageOut.model_validate(m) for m in messages],
        "preview": PreviewOut.model_validate(preview) if preview else None,
        "draft": DraftOut.model_validate(draft) if draft else None,
    }


@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: int, body: MessageIn, usecase: ExamChatUseCaseDep, writer: ReplyWriterDep):
    """Gửi một tin nhắn, nhận phản hồi qua SSE: message* → preview? → draft? → done (hoặc error)."""
    try:
        turn = await usecase.respond(session_id, body.text)
    except SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_SESSION) from None
    except Exception:  # lỗi không lường trước: báo qua SSE thay vì cắt kết nối
        log.exception("exam-chat respond failed")

        def failed() -> Iterator[str]:
            yield _sse("error", {"code": "internal_error", "message": "Có lỗi khi xử lý tin nhắn, em thử lại nhé."})

        return StreamingResponse(failed(), media_type="text/event-stream")

    def events() -> Iterator[str]:
        for chunk in writer.stream(turn.reply):
            yield _sse("message", {"delta": chunk})
        if turn.preview_changed and turn.preview is not None:
            yield _sse("preview", PreviewOut.model_validate(turn.preview).model_dump(mode="json"))
        if turn.draft is not None:
            yield _sse("draft", DraftOut.model_validate(turn.draft).model_dump(mode="json"))
        yield _sse("done", {"preview_version": turn.preview.version if turn.preview else None})

    return StreamingResponse(
        events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.get("/sessions/{session_id}/preview", response_model=PreviewOut)
async def get_preview(session_id: int, usecase: ExamChatUseCaseDep):
    try:
        return await usecase.get_preview(session_id)
    except SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_SESSION) from None
    except PreviewNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_PREVIEW) from None


@router.patch("/sessions/{session_id}/preview", response_model=PreviewOut)
async def update_preview(session_id: int, body: PreviewUpdate, usecase: ExamChatUseCaseDep):
    try:
        return await usecase.update_preview(session_id, body.edit, body.version)
    except SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_SESSION) from None
    except PreviewNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_PREVIEW) from None
    except VersionConflict as e:
        raise _conflict(e) from e
    except PreviewRuleError as e:
        raise _invalid(e) from e


@router.post("/sessions/{session_id}/preview/confirm", response_model=ConfirmOut)
async def confirm_preview(session_id: int, body: ConfirmIn, usecase: ExamChatUseCaseDep):
    """Xác nhận bản xem trước rồi dựng đề nháp từ câu đã duyệt."""
    try:
        preview, draft, message = await usecase.confirm(session_id, body.version)
    except SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_SESSION) from None
    except PreviewNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_PREVIEW) from None
    except VersionConflict as e:
        raise _conflict(e) from e
    except InvalidState as e:
        raise HTTPException(status.HTTP_409_CONFLICT, {"message": str(e)}) from e
    except PreviewRuleError as e:
        raise _invalid(e) from e
    return {"preview": preview, "draft": draft, "message": message}


@router.get("/sessions/{session_id}/draft", response_model=DraftOut)
async def get_draft(session_id: int, usecase: ExamChatUseCaseDep):
    try:
        draft = await usecase.latest_draft(session_id)
    except SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_SESSION) from None
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Phiên chưa có đề nháp")
    return draft
