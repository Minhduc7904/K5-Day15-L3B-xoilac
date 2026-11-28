"""Validate uploaded images and read their text through the existing OCR provider."""
import asyncio
import re
from dataclasses import dataclass

import httpx

from app.service.pdf_import_models import PdfImportModels, image_mime

MAX_CHAT_IMAGES = 4
MAX_CHAT_IMAGE_BYTES = 4 * 1024 * 1024
MAX_OCR_TEXT_PER_IMAGE = 3500
OCR_IMAGE_PLACEHOLDER = re.compile(r"!\[[^\]\n]*\]\([^\)\n]*\)")


class ExamChatImageError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass(frozen=True)
class PreparedImage:
    data: bytes
    mime: str


class ExamChatOcr:
    def __init__(self, models: PdfImportModels) -> None:
        self.models = models

    @staticmethod
    def prepare(images: list[bytes]) -> list[PreparedImage]:
        if not 1 <= len(images) <= MAX_CHAT_IMAGES:
            raise ExamChatImageError(422, "INVALID_IMAGE_COUNT", "Gửi từ 1 đến 4 ảnh mỗi lượt.")
        if sum(map(len, images)) > MAX_CHAT_IMAGE_BYTES:
            raise ExamChatImageError(413, "IMAGES_TOO_LARGE", "Tổng dung lượng ảnh tối đa 4 MB.")
        try:
            return [PreparedImage(data, image_mime(data)) for data in images]
        except ValueError as exc:
            raise ExamChatImageError(415, "UNSUPPORTED_IMAGE", "Chỉ nhận ảnh PNG, JPEG hoặc WebP hợp lệ.") from exc

    async def recognize(self, images: list[PreparedImage]) -> list[str]:
        if not self.models.ocr_key:
            raise ExamChatImageError(503, "OCR_UNAVAILABLE", "Đã lưu ảnh. Tính năng đọc ảnh chưa được cấu hình.")
        try:
            async with asyncio.timeout(25), asyncio.TaskGroup() as group:
                reads = [group.create_task(self._one(image.data, image.mime)) for image in images]
        except (TimeoutError, ExceptionGroup) as exc:
            raise ExamChatImageError(
                503, "OCR_UNAVAILABLE", "Chưa đọc được ảnh lúc này. Em thử lại hoặc nhập chủ đề Toán bằng chữ nhé.",
            ) from exc
        return [read.result() for read in reads]

    async def _one(self, data: bytes, mime: str) -> str:
        try:
            text = await self.models.recognize_image(data, mime)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise RuntimeError("OCR provider unavailable") from exc
        return OCR_IMAGE_PLACEHOLDER.sub("", text).strip()[:MAX_OCR_TEXT_PER_IMAGE]
