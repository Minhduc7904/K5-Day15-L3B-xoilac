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
# ĐÚNG MỘT worker: presence online và ticket socket (app/api/realtime.py) nằm trong bộ nhớ tiến trình.
# Nhiều worker cần Redis, xem docs/architecture/backend-realtime.md (#20).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
