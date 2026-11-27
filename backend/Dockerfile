FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=8

WORKDIR /app

# Cài thư viện trước để Docker cache lớp này khi chỉ đổi mã nguồn.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# Sau nginx: tin header X-Forwarded-* để URL chuyển hướng giữ đúng https. Cổng 8000 không mở ra Internet.
# asgi_app = Socket.IO (/api/socket.io) bọc FastAPI (#20).
# ĐÚNG MỘT worker: presence online và ticket socket nằm trong bộ nhớ tiến trình. Nhiều worker cần Redis
# (AsyncRedisManager cho Socket.IO + PresenceRegistry/ticket dùng Redis), xem docs/architecture/backend-realtime.md.
CMD ["uvicorn", "app.main:asgi_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
