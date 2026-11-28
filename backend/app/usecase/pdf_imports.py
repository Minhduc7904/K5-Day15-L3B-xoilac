import logging
import re
from io import BytesIO
from pathlib import PurePath
from uuid import uuid4

from botocore.exceptions import BotoCoreError, ClientError
from pypdf import PdfReader
from starlette.concurrency import run_in_threadpool

from app.repositories.pdf_imports import PdfImportRepository
from app.schemas.pdf_import import DraftEdit
from app.service.pdf_import_models import OcrPage, PdfImportModels, image_mime
from app.service.storage_service import StorageService
from app.usecase.pdf_import_answers import STATEMENT_TYPES, build_drafts, media_ids
from app.usecase.pdf_import_classification import classify_drafts
from app.usecase.pdf_import_question_source import reconcile_vector_choices
from app.usecase.pdf_import_solutions import worked_solutions

MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PAGES = 60
IMAGE_LINK = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
CHAPTER_CODE = re.compile(r"(10|11|12)C\d+")
logger = logging.getLogger(__name__)


class ImportErrorDetail(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def count_pdf_pages(data: bytes) -> int:
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ValueError
        return len(reader.pages)
    except Exception:
        raise ImportErrorDetail(422, "PDF không đọc được hoặc được mã hóa.") from None


class PdfImportUseCase:
    def __init__(
        self, repository: PdfImportRepository, storage: StorageService, models: PdfImportModels, bucket: str
    ) -> None:
        self.repo = repository
        self.storage = storage
        self.models = models
        self.bucket = bucket

    async def _save_file(self, name: str, data: bytes, mime: str, parent: int | None = None) -> int:
        extension = {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[mime]
        filename = f"{uuid4().hex}.{extension}"
        key = f"pdf-imports/{filename}"
        await self.storage.put(key, data, mime)
        return await self.repo.add_media(
            file_name=filename, original_name=name, mime_type=mime, file_size=len(data),
            type="IMAGE" if parent is not None else "DOCUMENT", status="READY",
            bucket_name=self.bucket, object_key=key, parent_id=parent,
        )

    async def upload(self, filename: str, data: bytes):
        if len(data) > MAX_PDF_BYTES:
            raise ImportErrorDetail(413, "PDF tối đa 20 MiB.")
        if not data.startswith(b"%PDF-"):
            raise ImportErrorDetail(415, "Đầu vào phải là PDF.")
        page_count = await run_in_threadpool(count_pdf_pages, data)
        if not 1 <= page_count <= MAX_PAGES:
            raise ImportErrorDetail(422, f"PDF phải có từ 1 đến {MAX_PAGES} trang.")
        name = PurePath(filename.replace("\\", "/")).name[:255] or "exam.pdf"
        media_id = await self._save_file(name, data, "application/pdf")
        row = await self.repo.add_import(original_media_id=media_id, filename=name, page_count=page_count)
        await self.repo.session.commit()
        return row

    async def _normalize_page(self, page: OcrPage, original_id: int) -> tuple[dict, list[str]]:
        identifiers = {}
        warnings = []
        for image in page.images:
            name = image.reference
            if name in identifiers:
                raise ValueError("Mã ảnh OCR bị trùng trên một trang.")
            try:
                mime = image_mime(image.data)
                assert image.data is not None
                identifiers[name] = await self._save_file(name[:255], image.data, mime, original_id)
            except (ValueError, OSError, BotoCoreError, ClientError):
                warnings.append(f"Trang {page.index + 1}: không lưu được hình {name}.")
                identifiers[name] = None

        def replace(match: re.Match) -> str:
            ref = match[2]
            if ref in identifiers and identifiers[ref] is not None:
                token = f"media:{identifiers[ref]}"
                return f"![{token}]({token})"
            marker = f"media-missing:p{page.index + 1}-{match.start()}"
            warnings.append(f"Trang {page.index + 1}: liên kết hình thiếu dữ liệu ({marker}).")
            return f"![{marker}]({marker})"

        return {
            "page": page.index + 1, "markdown": page.markdown,
            "normalized": IMAGE_LINK.sub(replace, page.markdown),
        }, warnings

    async def process(self, import_id: int) -> None:
        row = await self.repo.get_import(import_id)
        if row is None or row.status != "queued":
            return
        session = self.repo.session
        stage = "ocr"
        try:
            row.status, row.stage = "processing", stage
            await session.commit()
            source = await self.repo.get_media(row.original_media_id, row.original_media_id)
            original = await self.storage.get(source["object_key"]) if source else None
            if not original:
                raise ValueError("PDF gốc không tồn tại.")
            row.ocr_model, pages = await self.models.recognize(original[0], page_count=row.page_count)
            if [p.index for p in pages] != list(range(row.page_count)):
                raise ValueError("OCR không trả đủ số trang theo thứ tự.")
            stage = row.stage = "media"
            await session.commit()
            normalized, warnings = [], []
            for page in pages:
                stored_page, page_warnings = await self._normalize_page(page, row.original_media_id)
                normalized.append(stored_page)
                warnings.extend(page_warnings)
            row.pages, row.warnings = normalized, warnings
            stage = row.stage = "extract"
            await session.commit()
            _, solutions = worked_solutions({page["page"]: page["normalized"] for page in normalized})
            source_keys = [key for key, block in solutions.items() if block is not None]
            row.extraction_model, extraction = await self.models.extract(normalized, source_solution_keys=source_keys)
            drafts = build_drafts(extraction, normalized)
            if not drafts:
                raise ValueError("Không tìm thấy câu hỏi có nguồn.")
            try:
                await run_in_threadpool(reconcile_vector_choices, original[0], drafts)
            except Exception as exc:
                logger.warning("PDF import %s text-layer comparison unavailable (%s)", import_id, type(exc).__name__)
            stage = row.stage = "classify"
            await session.commit()
            try:
                async with session.begin_nested():
                    await classify_drafts(drafts, self.repo, self.models)
            except Exception as exc:
                logger.warning("PDF import %s classification unavailable (%s)", import_id, type(exc).__name__)
                row.warnings = [*row.warnings, "Chưa lấy được gợi ý nhãn. Hãy gắn nhãn khi duyệt."]
                for draft in drafts:
                    draft["flags"].append("label_review")
            for position, draft in enumerate(drafts, 1):
                self.repo.add_draft(row.id, position, draft)
            row.status, row.stage = "ready_for_review", "review"
            await session.commit()
        except Exception as exc:
            logger.warning("PDF import %s failed at %s (%s)", import_id, stage, type(exc).__name__)
            await session.rollback()
            row = await self.repo.get_import(import_id)
            row.status, row.stage = "failed", stage
            row.error = f"Không hoàn thành bước {stage}. Kiểm tra tệp hoặc cấu hình rồi tải lại."
            await session.commit()

    async def get_import(self, import_id: int):
        row = await self.repo.get_import(import_id)
        if row is None:
            raise ImportErrorDetail(404, "Không tìm thấy phiên nhập.")
        return row

    async def list_imports(self, offset: int, limit: int):
        return await self.repo.list_imports(offset, limit)

    @property
    def providers_configured(self) -> bool:
        return self.models.configured

    async def list_drafts(self, import_id: int):
        await self.get_import(import_id)
        return await self.repo.get_drafts(import_id)

    async def get_draft(self, import_id: int, draft_id: int, *, lock: bool = False):
        draft = await self.repo.get_draft(import_id, draft_id, lock=lock)
        if draft is None:
            raise ImportErrorDetail(404, "Không tìm thấy bản nháp.")
        return draft

    async def edit(self, import_id: int, draft_id: int, edit: DraftEdit):
        draft = await self.get_draft(import_id, draft_id, lock=True)
        if draft.status != "pending":
            raise ImportErrorDetail(409, "Bản nháp đã có quyết định.")
        changes = edit.model_dump(exclude_unset=True)
        if any(key in changes and changes[key] is None for key in ("content", "statements", "chapterCodes", "imageReviewed")):
            raise ImportErrorDetail(422, "Trường đã sửa không được để null.")
        if changes.keys() & {"content", "statements", "solution"} and "imageReviewed" not in changes:
            changes["imageReviewed"] = False
        if changes.keys() & {"statements", "correctAnswer"}:
            changes["answerState"] = "edited"
        draft.payload = {**draft.payload, **changes}
        await self.repo.session.commit()
        return draft

    async def decide(self, import_id: int, draft_id: int, *, approve: bool):
        draft = await self.get_draft(import_id, draft_id, lock=True)
        if draft.status == ("approved" if approve else "rejected"):
            return draft
        if draft.status != "pending":
            raise ImportErrorDetail(409, "Bản nháp đã có quyết định.")
        if approve:
            draft.question_id = await self._publish(import_id, draft)
        draft.status = "approved" if approve else "rejected"
        await self.repo.session.commit()
        return draft

    async def _publish(self, import_id: int, draft) -> int:
        data = draft.payload
        options = data["statements"]
        question_type = data["type"]
        answer = data["correctAnswer"]
        if not data["content"].strip() or any(not option["content"].strip() for option in options):
            raise ImportErrorDetail(422, "Nội dung câu hỏi hoặc mệnh đề còn trống.")
        if question_type in STATEMENT_TYPES:
            if len(options) < 2 or any(option["isCorrect"] is None for option in options):
                raise ImportErrorDetail(422, "Chưa xác nhận đủ đáp án cho các mệnh đề.")
            correct_count = sum(option["isCorrect"] for option in options)
            if (question_type == "SINGLE_CHOICE" and correct_count != 1) or (
                question_type == "MULTIPLE_CHOICE" and correct_count < 2
            ):
                raise ImportErrorDetail(422, "Số lựa chọn đúng không phù hợp loại câu.")
            answer = None
        elif options or not ((answer and answer.strip()) or (
            question_type == "ESSAY" and data["answerState"] not in {"ambiguous", "conflict"}
            and data["solution"] and data["solution"].strip()
        )):
            raise ImportErrorDetail(422, "Câu trả lời cần kết quả hoặc lời giải hợp lệ.")
        contents = [data["content"], data["solution"], *(o["content"] for o in options)]
        if any("media-missing:" in value for value in contents if value):
            raise ImportErrorDetail(422, "Còn tham chiếu hình thiếu dữ liệu.")
        if any(not re.fullmatch(r"media:\d+", image[2])
               for value in contents if value for image in IMAGE_LINK.finditer(value)):
            raise ImportErrorDetail(422, "Hình Markdown phải tham chiếu media của phiên nhập.")
        refs = media_ids(*contents)
        if data["imageDependent"] and not refs:
            raise ImportErrorDetail(422, "Cần có hình cho câu phụ thuộc hình.")
        needs_image_review = refs or data["imageDependent"] or any(
            flag in data["flags"] for flag in ("image_source_mismatch", "image_unplaced")
        )
        if needs_image_review and not data["imageReviewed"]:
            raise ImportErrorDetail(422, "Cần có hình và xác nhận đã kiểm tra hình.")
        row = await self.get_import(import_id)
        for media_id in refs:
            asset = await self.get_asset(import_id, media_id, original=row.original_media_id, image_only=True)
            if await self.storage.get(asset["object_key"]) is None:
                raise ImportErrorDetail(422, "Hình tham chiếu không còn trong kho.")
        codes = list(dict.fromkeys(data["chapterCodes"]))
        if not codes or any(not CHAPTER_CODE.fullmatch(code) for code in codes) or not data["difficulty"]:
            raise ImportErrorDetail(422, "Cần xác nhận mã chương và độ khó.")
        available = await self.repo.get_chapters(codes)
        if len(available) != len(codes) or len({ch["subject_id"] for ch in available}) != 1 or len({c[:2] for c in codes}) != 1:
            raise ImportErrorDetail(422, "Mã chương không tồn tại hoặc không cùng khối.")
        return await self.repo.publish(
            {"content": data["content"], "slug": f"pdf-import-{import_id}-{draft.id}",
             "type": question_type, "correct_answer": answer, "solution": data["solution"],
             "difficulty": data["difficulty"], "grade": int(codes[0][:2]), "subject_id": available[0]["subject_id"]},
            options, [ch["chapter_id"] for ch in available],
        )

    async def get_asset(self, import_id: int, media_id: int, *, original: int | None = None, image_only: bool = False):
        if original is None:
            original = (await self.get_import(import_id)).original_media_id
        asset = await self.repo.get_media(original, media_id)
        if not asset or asset["status"] != "READY" or (image_only and asset["type"] != "IMAGE"):
            raise ImportErrorDetail(422 if image_only else 404, "Không tìm thấy hình hoặc PDF.")
        return asset

    async def download(self, import_id: int, media_id: int):
        asset = await self.get_asset(import_id, media_id)
        stored = await self.storage.get(asset["object_key"])
        if stored is None:
            raise ImportErrorDetail(404, "Tệp không còn trong kho.")
        return stored[0], asset["mime_type"]
