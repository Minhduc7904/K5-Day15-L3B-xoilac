# Các location dùng chung cho cổng 80 và 443 (include trong từng khối server của default.conf).

location = /healthz {
    access_log off;
    default_type text/plain;
    return 200 "ok\n";
}

# Socket.IO (issue #20): nâng cấp lên WebSocket và giữ kết nối lâu.
# `^~` để location này thắng location regex bên dưới.
location ^~ /api/socket.io/ {
    set $backend http://backend:8000;
    proxy_pass $backend;
    include /etc/nginx/conf.d/proxy.inc;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_read_timeout 1h;
    proxy_send_timeout 1h;
    proxy_buffering off;
}

# Callback chứa mã OAuth dùng một lần, nên tắt access log ở đường dẫn này.
location = /api/auth/google/callback {
    access_log off;
    set $backend http://backend:8000;
    proxy_pass $backend;
    include /etc/nginx/conf.d/proxy.inc;
    proxy_set_header Connection "";
}

# API và tài liệu tự sinh của FastAPI.
location ~ ^/(api/|docs|redoc|openapi\.json) {
    set $backend http://backend:8000;
    proxy_pass $backend;
    include /etc/nginx/conf.d/proxy.inc;
    proxy_set_header Connection "";
    proxy_read_timeout 120s;
    # SSE (issue #4): không gom bộ đệm để sự kiện đến ngay.
    proxy_buffering off;
}

location / {
    default_type text/plain;
    return 404 "Examind: dung /api/v1/health de kiem tra backend.\n";
}
