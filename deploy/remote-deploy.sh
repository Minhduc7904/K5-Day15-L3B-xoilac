#!/usr/bin/env bash
# Chạy TRÊN VPS (workflow deploy.yml đưa script này qua SSH: `bash -s -- <sha> < deploy/remote-deploy.sh`).
# Các bước: đồng bộ git → compose up --build → kiểm cú pháp và reload nginx → kiểm sức khoẻ → dọn Docker.
# Kiểm sức khoẻ lỗi thì quay lại commit trước và dựng lại.
set -euo pipefail

SHA="${1:-}"
APP="${APP_DIR:-/opt/examind/app}"
ENV_FILE="${ENV_FILE:-/opt/examind/prod.env}"
BRANCH="${BRANCH:-main}"   # chỉ đổi khi thử tay trên nhánh khác

compose() {
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.prod.yml "$@"
}

cleanup() {
  echo "== Dọn Docker"
  docker image prune -f >/dev/null || true
  docker builder prune -f --keep-storage 1GB >/dev/null || true
  # Không bao giờ dùng --volumes: volume pgdata và miniodata là dữ liệu thật.
  docker system df || true
  df -h / | tail -1
}
trap cleanup EXIT

apply() {
  compose up -d --build --remove-orphans
  # Cấu hình nginx được mount vào container nên container không tự đổi khi file đổi: luôn kiểm và reload.
  compose exec -T nginx nginx -t
  compose exec -T nginx nginx -s reload
}

healthy() {
  for _ in $(seq 1 40); do
    if curl -fsS --max-time 5 http://127.0.0.1/api/v1/health | grep -q '"status":"ok"'; then
      return 0
    fi
    sleep 3
  done
  return 1
}

[ -f "$ENV_FILE" ] || { echo "Thiếu $ENV_FILE (chạy deploy/bootstrap-vps.sh trước)"; exit 1; }
cd "$APP"
PREV="$(git rev-parse HEAD)"
git fetch --prune origin "$BRANCH"
git reset --hard "${SHA:-origin/$BRANCH}"
echo "== Deploy $(git rev-parse --short HEAD) (trước đó $(git rev-parse --short "$PREV"))"

if apply && healthy; then
  compose ps
  echo "== Deploy thành công"
  exit 0
fi

echo "== Deploy lỗi, in log rồi quay lại $(git rev-parse --short "$PREV")"
compose ps || true
compose logs --tail=60 backend nginx db-init minio-init || true
git reset --hard "$PREV"
apply || true
healthy && echo "== Đã quay lại bản trước, dịch vụ chạy lại" || echo "== Bản trước cũng không khoẻ, cần kiểm tay"
exit 1
