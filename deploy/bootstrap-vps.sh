#!/usr/bin/env bash
# Chạy MỘT LẦN trên VPS Ubuntu mới (có sudo): cài Docker, thêm swap, tạo thư mục, clone repo, sinh prod.env.
# Chạy lại an toàn: bước nào xong rồi thì bỏ qua. Không in mật khẩu ra màn hình.
#   ssh ubuntu@<host> 'bash -s' < deploy/bootstrap-vps.sh
set -euo pipefail

REPO="${REPO_URL:-https://github.com/Minhduc7904/K5-Day15-L3B-xoilac.git}"
BASE=/opt/examind
SWAP_GB="${SWAP_GB:-2}"

echo "== Docker"
if ! command -v docker >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  sudo apt-get update -qq
  sudo -E apt-get install -y -qq docker.io docker-compose-v2 git curl
  sudo systemctl enable --now docker
fi
docker --version
id -nG | tr ' ' '\n' | grep -qx docker || sudo usermod -aG docker "$USER"

echo "== Swap ${SWAP_GB}G (VPS chỉ có ~1,9 GB RAM, build image cần thêm bộ nhớ)"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l "${SWAP_GB}G" /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null
  sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo "== Thư mục và mã nguồn"
sudo install -d -o "$USER" -g "$USER" "$BASE" "$BASE/seed"
chmod 700 "$BASE/seed"
[ -d "$BASE/app/.git" ] || git clone --depth 50 "$REPO" "$BASE/app"

echo "== $BASE/prod.env"
if [ ! -f "$BASE/prod.env" ]; then
  umask 077
  {
    echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)"
    echo "S3_ACCESS_KEY=examind"
    echo "S3_SECRET_KEY=$(openssl rand -hex 16)"
    echo "SEED_DIR=$BASE/seed"
    echo "CORS_ORIGINS=http://localhost:3000,https://examind-frontend.vercel.app"
  } > "$BASE/prod.env"
  echo "Đã tạo prod.env (mật khẩu sinh ngẫu nhiên, chỉ chủ file đọc được)."
else
  echo "prod.env đã có, giữ nguyên."
fi
echo "== Xong. Đăng nhập lại để quyền nhóm docker có hiệu lực."
