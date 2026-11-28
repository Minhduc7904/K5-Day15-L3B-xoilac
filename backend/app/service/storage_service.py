import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings


class StorageService:
    """Giao tiếp MinIO qua API tương thích S3. boto3 là đồng bộ nên gọi trong threadpool."""

    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name="us-east-1",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await run_in_threadpool(
            self._client.put_object, Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )

    async def delete(self, key: str) -> None:
        await run_in_threadpool(self._client.delete_object, Bucket=self._bucket, Key=key)

    async def get(self, key: str, bucket: str | None = None) -> tuple[bytes, str] | None:
        """Đọc đối tượng. `bucket` mặc định là bucket của ứng dụng; ảnh nền seed nằm ở bucket riêng (images, documents…)."""
        def _get(name: str) -> tuple[bytes, str] | None:
            try:
                obj = self._client.get_object(Bucket=name, Key=key)
            except ClientError as e:
                if e.response["Error"]["Code"] in ("NoSuchKey", "NoSuchBucket", "404"):
                    return None
                raise
            return obj["Body"].read(), obj.get("ContentType", "application/octet-stream")

        found = await run_in_threadpool(_get, bucket or self._bucket)
        if found is None and bucket and bucket != self._bucket:
            found = await run_in_threadpool(_get, self._bucket)
        return found

    async def ping(self) -> bool:
        try:
            await run_in_threadpool(self._client.head_bucket, Bucket=self._bucket)
            return True
        except Exception:
            return False
