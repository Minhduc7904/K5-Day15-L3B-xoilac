import pytest

from app.service.media_image import load_media_image


class BucketStorage:
    """Giả MinIO nhiều bucket: ảnh seed nằm ở bucket `images`, không phải bucket mặc định."""

    def __init__(self, objects):
        self.objects = objects  # {(bucket, key): (data, content_type)}
        self.default = "examind"

    async def get(self, key, bucket=None):
        return self.objects.get((bucket or self.default, key))


@pytest.mark.asyncio
async def test_image_is_read_from_its_own_bucket():
    storage = BucketStorage({("images", "questions/5/question-5.jpg"): (b"jpg", "image/jpeg")})
    found = await load_media_image(storage, ("images", "questions/5/question-5.jpg", "image/jpeg"))
    assert found == (b"jpg", "image/jpeg")


@pytest.mark.asyncio
async def test_missing_content_type_falls_back_to_media_row():
    storage = BucketStorage({("images", "a.jpg"): (b"jpg", "application/octet-stream")})
    assert await load_media_image(storage, ("images", "a.jpg", "image/jpeg")) == (b"jpg", "image/jpeg")


@pytest.mark.asyncio
async def test_non_image_or_missing_object_is_rejected():
    storage = BucketStorage({("documents", "a.pdf"): (b"pdf", "application/pdf")})
    assert await load_media_image(storage, ("documents", "a.pdf", "application/pdf")) is None
    assert await load_media_image(storage, ("images", "none.jpg", "image/jpeg")) is None
    assert await load_media_image(storage, None) is None
