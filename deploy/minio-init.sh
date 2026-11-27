#!/bin/sh
# Container minio-init: tạo bucket và nạp ảnh nền đúng MỘT lần. Chạy xong thì thoát.
# Gói ảnh nằm ở /seed/minio/<bucket>/<object_key> (do backend/scripts/build_seed.py dựng).
set -eu

mc alias set local http://minio:9000 "$S3_ACCESS_KEY" "$S3_SECRET_KEY" >/dev/null
mc mb --ignore-existing "local/$S3_BUCKET"

MARKER="local/$S3_BUCKET/.init/base-seed"
if [ ! -d /seed/minio ]; then
  echo "[minio-init] Không có gói ảnh nền, chỉ tạo bucket."
  exit 0
fi
if mc stat "$MARKER" >/dev/null 2>&1; then
  echo "[minio-init] Đã nạp ảnh nền trước đó, bỏ qua."
  exit 0
fi

for dir in /seed/minio/*/; do
  bucket="$(basename "$dir")"
  mc mb --ignore-existing "local/$bucket"
  mc mirror --quiet --overwrite "$dir" "local/$bucket"
  echo "[minio-init] $bucket: $(mc ls --recursive "local/$bucket" | wc -l) đối tượng"
done
echo "done" | mc pipe "$MARKER"
echo "[minio-init] Hoàn tất."
