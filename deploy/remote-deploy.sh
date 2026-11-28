#!/usr/bin/env bash
# Chạy TRÊN VPS (workflow deploy.yml đưa script này qua SSH: `bash -s -- <sha> < deploy/remote-deploy.sh`).
# Các bước: đồng bộ git → chứng chỉ tạm nếu cần → compose up --build → kiểm cú pháp và reload nginx
# → kiểm sức khoẻ → xin chứng chỉ HTTPS lần đầu → dọn Docker.
# Kiểm sức khoẻ lỗi thì quay lại commit trước và dựng lại.
set -euo pipefail

SHA="${1:-}"
APP="${APP_DIR:-/opt/examind/app}"
ENV_FILE="${ENV_FILE:-/opt/examind/prod.env}"
BRANCH="${BRANCH:-main}"   # chỉ đổi khi thử tay trên nhánh khác
DOMAIN="${DOMAIN:-examind.duckdns.org}"
# Hai thư mục này được mount vào nginx và certbot (xem docker-compose.prod.yml).
export LETSENCRYPT_DIR="${LETSENCRYPT_DIR:-/opt/examind/letsencrypt}"
export CERTBOT_WEBROOT="${CERTBOT_WEBROOT:-/opt/examind/certbot-www}"

compose() {
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.prod.yml "$@"
}

# nginx cần có file chứng chỉ mới khởi động được khối 443. Chưa có chứng chỉ thật thì tạo bản tự ký tạm.
ensure_placeholder_cert() {
  local live="$LETSENCRYPT_DIR/live/$DOMAIN"
  sudo install -d -m 755 "$CERTBOT_WEBROOT"
  # The deploy user may be unable to traverse Certbot's root-owned archive directory.
  if sudo test -s "$live/fullchain.pem" && sudo test -s "$live/privkey.pem"; then
    return 0
  fi
  if sudo test -f "$LETSENCRYPT_DIR/renewal/$DOMAIN.conf" \
    || sudo test -L "$live/fullchain.pem" || sudo test -L "$live/privkey.pem"; then
    echo "== Bộ chứng chỉ Certbot chưa đủ tệp cho $DOMAIN. Kiểm tra live/archive." >&2
    return 1
  fi
  sudo install -d -m 755 "$live"
  sudo openssl req -x509 -nodes -newkey rsa:2048 -days 30 -subj "/CN=$DOMAIN" \
    -keyout "$live/privkey.pem" -out "$live/fullchain.pem" 2>/dev/null
}

# Xin chứng chỉ Let's Encrypt lần đầu (HTTP-01 qua cổng 80). Đã có thì bỏ qua: container certbot tự gia hạn.
# Lỗi ở đây không làm hỏng deploy: API vẫn chạy qua HTTP, lần deploy sau sẽ thử lại.
obtain_certificate() {
  sudo test -f "$LETSENCRYPT_DIR/renewal/$DOMAIN.conf" && return 0
  echo "== Xin chứng chỉ Let's Encrypt cho $DOMAIN"
  sudo rm -rf "$LETSENCRYPT_DIR/live/$DOMAIN" "$LETSENCRYPT_DIR/archive/$DOMAIN"
  if compose run --rm --no-deps --entrypoint certbot certbot certonly \
      --webroot -w /var/www/certbot -d "$DOMAIN" --cert-name "$DOMAIN" \
      --non-interactive --agree-tos --register-unsafely-without-email; then
    compose exec -T nginx nginx -s reload
    echo "== Đã cấp chứng chỉ cho $DOMAIN"
  else
    echo "== CẢNH BÁO: chưa xin được chứng chỉ (cổng 80 và 443 đã mở trong Security Group? DNS trỏ đúng IP?)"
    ensure_placeholder_cert
    return 1
  fi
}

check_https() {
  curl -fsS --max-time 10 --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/api/v1/health/live" \
    && echo && echo "== HTTPS hoạt động" \
    || echo "== HTTPS chưa dùng được (chứng chỉ tạm hoặc cổng 443 lỗi)"
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
  ensure_placeholder_cert || return 1
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
  obtain_certificate || true
  check_https
  compose ps
  echo "== Deploy thành công"
  exit 0
fi

echo "== Deploy lỗi, in log rồi quay lại $(git rev-parse --short "$PREV")"
compose ps || true
compose logs --tail=60 backend student-worker nginx db-init minio-init || true
git reset --hard "$PREV"
apply || true
healthy && echo "== Đã quay lại bản trước, dịch vụ chạy lại" || echo "== Bản trước cũng không khoẻ, cần kiểm tay"
exit 1
