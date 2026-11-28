IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp", "image/gif", "image/avif"}


async def load_media_image(storage, location: tuple[str, str, str] | None) -> tuple[bytes, str] | None:
    """Đọc ảnh theo dòng `media` (bucket, object_key, mime_type). Trả None nếu thiếu hoặc không phải ảnh.

    Ảnh nền seed nằm ở bucket riêng (images, documents…) và nạp bằng `mc mirror` nên MinIO có thể không giữ
    Content-Type; khi đó dùng `mime_type` ghi trong bảng media.
    """
    if not location:
        return None
    bucket, key, recorded = location
    found = await storage.get(key, bucket)
    if not found:
        return None
    data, stored = found
    mime = stored if stored in IMAGE_MIMES else "image/jpeg" if recorded == "image/jpg" else recorded
    return (data, mime) if mime in IMAGE_MIMES else None
