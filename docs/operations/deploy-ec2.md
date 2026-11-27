# Truy cập VPS AWS EC2 · Examind

Dùng runbook này để đăng nhập VPS demo qua SSH, cấu hình backend production và kiểm tra API dành cho frontend.

## Điều kiện trước khi chạy

- Máy cá nhân có OpenSSH và tệp `.pem` được cấp cho instance.
- Security Group cho phép TCP 22 từ IP nguồn của máy cá nhân. Ghim host key vào `known_hosts` sau khi đối chiếu fingerprint với system log của đúng instance trong AWS Console. Nếu thiếu fingerprint đáng tin cậy hoặc fingerprint không khớp, dừng kết nối.
- Các lệnh PowerShell bên dưới chạy từ thư mục gốc repo nếu khóa được lưu tại `backend-key.pem`. Git bỏ qua các tệp `.pem` theo quy tắc có sẵn trong `.gitignore`. Nhận khóa qua kênh riêng của nhóm.

## Thông tin môi trường

| Thông tin | Giá trị |
| --- | --- |
| Instance | Examind (`i-0931f2a3b4010b6b3`) |
| Vùng AWS | Sydney (`ap-southeast-2`) |
| Loại instance | `t8i.small` |
| Hệ điều hành | Ubuntu 26.04.1 LTS |
| IPv4 công khai (Elastic IP) | `54.79.136.46` |
| Tên miền | `examind.duckdns.org` (DuckDNS, trỏ về Elastic IP) |
| DNS công khai của AWS | `ec2-54-79-136-46.ap-southeast-2.compute.amazonaws.com` |
| SSH | `ubuntu`, cổng `22` |
| Thư mục triển khai | `/opt/examind/app` |
| Cấu hình production | `/opt/examind/prod.env`, thuộc tài khoản triển khai, quyền `0600` |

Ngày 27/11/2026 instance được gắn **Elastic IP** `54.79.136.46` (thay cho IP cấp tự động `32.236.15.241`), nên IP không đổi khi dừng rồi khởi động lại. AWS tính phí mọi IPv4 công khai (kể cả Elastic IP đang gắn vào instance; tài khoản free tier được miễn 750 giờ/tháng trong 12 tháng đầu), nên khi không dùng nữa hãy giải phóng (Release) trong **EC2 → Elastic IPs** để khỏi bị tính phí. Tên miền `examind.duckdns.org` cấu hình trên [duckdns.org](https://www.duckdns.org). Nếu Elastic IP đổi, cập nhật ô current ip ở DuckDNS và các secret `EC2_HOST`, `EC2_KNOWN_HOSTS` (xem [deploy-backend-ci-cd.md](deploy-backend-ci-cd.md)).

## Các bước thực hiện

1. **Kết nối SSH.** Từ thư mục gốc repo, chạy lệnh sau hoặc thay đường dẫn sau `-i` bằng vị trí tệp của bạn.

   ```powershell
   ssh -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -i .\backend-key.pem -p 22 ubuntu@54.79.136.46
   ```

   Trên macOS hoặc Linux, dùng đường dẫn `./backend-key.pem`.

2. **Tra địa chỉ API cho frontend.** Backend được phục vụ qua nginx ở cổng 80 và **443** (cổng 8000 chỉ nghe nội bộ trên VPS, không mở ra ngoài). Frontend trên Vercel (HTTPS) phải dùng địa chỉ HTTPS, nếu không trình duyệt chặn vì mixed content.

   ```text
   API:    https://examind.duckdns.org/api/v1
   Socket: wss://examind.duckdns.org   (đường dẫn /api/socket.io, issue #20)
   ```

   Chứng chỉ Let's Encrypt do `deploy/remote-deploy.sh` xin ở lần deploy đầu và container `certbot` tự gia hạn. Cần cả cổng **80** (xác minh tên miền) và **443** mở trong Security Group. Cổng 80 vẫn phục vụ API qua HTTP để kiểm sức khoẻ. Frontend gọi từ origin khác thì cho phép origin đó trong `CORS_ORIGINS` của `/opt/examind/prod.env` trên VPS (nhiều origin phân tách bằng dấu phẩy).

## Cập nhật cấu hình production

`deploy/remote-deploy.sh` dùng `--env-file /opt/examind/prod.env` với cả hai tệp Compose. Tệp này nằm ngoài checkout nên lần triển khai sau vẫn dùng cấu hình đã lưu. Compose chỉ truyền cho backend các biến được khai báo trong cấu hình dịch vụ.

| Nhóm | Biến và cách dùng |
| --- | --- |
| PostgreSQL | `POSTGRES_PASSWORD` bắt buộc. Compose ghép `DATABASE_URL` từ mật khẩu, `POSTGRES_USER` và `POSTGRES_DB`. Giữ giá trị của cơ sở dữ liệu đang chạy. |
| MinIO | `S3_ACCESS_KEY` và `S3_SECRET_KEY` bắt buộc. Giữ `S3_BUCKET` hiện dùng. Compose đặt endpoint nội bộ `http://minio:9000`. |
| CORS và xác thực | Giữ `CORS_ORIGINS` cho các origin frontend cần truy cập trực tiếp, `COOKIE_SECURE=true` trên HTTPS và cấu hình phiên hiện tại. Giữ `ADMIN_*` nếu dùng bootstrap cùng các biến OTP, Gmail và Google OAuth đã bật. Xem [cấu hình xác thực](deploy-backend-ci-cd.md#cấu-hình-otp-và-google). |
| Nhập đề PDF | `MISTRAL_API_KEY` và `OPENAI_API_KEY` bật OCR, tách câu hỏi và embedding. Thiếu một trong hai khóa thì API tải PDF trả `503`. Tên model dùng mặc định của backend. |

1. Thống nhất thời điểm thay đổi với người vận hành và kiểm tra đang dùng đúng thư mục, tệp env và tài khoản triển khai. Chạy trên EC2 với tài khoản đó để lưu bản sao và tạo tệp chuẩn bị trong cùng thư mục.

   ```bash
   cd /opt/examind/app
   stat -c '%U %a %n' /opt/examind/prod.env
   umask 077
   backup=$(mktemp /opt/examind/prod.env.backup.XXXXXX)
   candidate=$(mktemp /opt/examind/prod.env.pending.XXXXXX)
   install -m 600 /opt/examind/prod.env "$backup"
   install -m 600 /opt/examind/prod.env "$candidate"
   ```

2. Chuyển riêng các khóa AI cần bổ sung qua stdin của SSH đã xác minh host key. Cập nhật các dòng tương ứng trong `$candidate`, giữ các giá trị hiện có và các dòng khác. Chạy với shell tracing tắt. Chỉ ghi tên biến và kết quả kiểm vào log. Sau khi xác nhận cấu hình hợp lệ, cài tệp bằng thao tác đổi tên trong cùng thư mục.

   ```bash
   if docker compose --env-file "$candidate" -f docker-compose.yml -f docker-compose.prod.yml config --quiet >/dev/null 2>&1; then
     mv -T -- "$candidate" /opt/examind/prod.env
   else
     echo 'Cấu hình Compose chưa hợp lệ. Kiểm tra lại tệp chuẩn bị trên EC2.' >&2
   fi
   ```

3. Kiểm tra phiên bản triển khai đã có hai biến AI trong `docker-compose.prod.yml`. Ghi ID container trước và sau lần triển khai đã thống nhất để xác nhận backend được dựng lại. Nếu Compose hiện tại đã có ánh xạ và chỉ cần nạp lại env, dựng lại riêng backend với image hiện tại. Chạy các lệnh này từ `/opt/examind/app`.

   ```bash
   compose() {
     docker compose --env-file /opt/examind/prod.env -f docker-compose.yml -f docker-compose.prod.yml "$@"
   }
   compose ps -q backend
   compose up -d --no-deps --no-build --force-recreate backend
   compose ps -q backend
   ```

## Kiểm tra kết quả

Sau khi SSH thành công, chạy trên EC2.

```bash
whoami
hostname
cat /var/lib/cloud/data/instance-id
grep ^PRETTY_NAME= /etc/os-release
```

Kết quả đã xác nhận là user `ubuntu`, hostname `ip-172-31-20-96` và instance ID `i-0931f2a3b4010b6b3`. Lần kiểm tra ngày 27/11/2026 chỉ thấy SSH lắng nghe trên giao diện công khai và chưa tìm thấy lệnh `docker` trong `PATH` của user `ubuntu`.

Từ ngày 27/11/2026, VPS đã cài Docker và chạy backend qua nginx. Xem [quy trình triển khai tự động](deploy-backend-ci-cd.md). Trên EC2, dùng hàm `compose` ở trên để xem trạng thái và kiểm tra khóa AI trong container mới. Kết quả `True` chỉ xác nhận khóa đã được nạp.

```bash
compose ps --all
compose exec -T backend python -c 'import os; print({name: bool(os.environ.get(name)) for name in ("MISTRAL_API_KEY", "OPENAI_API_KEY")})'
```

Từ ngoài EC2, kiểm tra HTTPS. Kết quả mong đợi là HTTP 200 với `status` là `ok` và cả `database` lẫn `storage` là `true`. Endpoint chạy `SELECT 1` và kiểm bucket MinIO qua backend.

```bash
curl -fsS --max-time 10 https://examind.duckdns.org/api/v1/health
```

Nếu đã bật OCR, dùng một trang PDF tổng hợp qua các adapter của backend trong container để gọi Mistral OCR, OpenAI tách câu và embedding một lượt. Ghi kết quả và chi phí ước tính. API tải PDF tạo bản ghi và lưu tệp vào MinIO. Dùng môi trường kiểm thử riêng khi cần xác minh toàn bộ API tải và đọc bản nháp.

## Quay lui cấu hình

Trong cửa sổ vận hành đã thống nhất, đặt `backup` về đúng đường dẫn bản sao của lần cập nhật. Khôi phục bằng tệp tạm quyền `0600`, kiểm cấu hình rồi dựng lại riêng backend. Kiểm lại `/api/v1/health`. Giữ nguyên các volume PostgreSQL và MinIO.

```bash
restored=$(mktemp /opt/examind/prod.env.restore.XXXXXX)
if install -m 600 "$backup" "$restored" \
  && docker compose --env-file "$restored" -f docker-compose.yml -f docker-compose.prod.yml config --quiet >/dev/null 2>&1; then
  mv -T -- "$restored" /opt/examind/prod.env \
    && compose up -d --no-deps --no-build --force-recreate backend
else
  echo 'Không thể xác minh bản sao cấu hình. Kiểm tra lại trên EC2.' >&2
fi
```

## Xử lý lỗi

| Triệu chứng | Kiểm tra |
| --- | --- |
| `UNPROTECTED PRIVATE KEY FILE` | Trên Windows, mở **Properties → Security → Advanced** của đúng tệp `.pem`, tắt kế thừa và giữ quyền truy cập cho tài khoản đang chạy SSH. Trên macOS hoặc Linux, dùng `chmod 600 ./backend-key.pem`. |
| `Permission denied (publickey)` | Kiểm tra username `ubuntu`, đường dẫn khóa và key pair của instance. |
| `Connection timed out` | Kiểm tra địa chỉ hiện tại, trạng thái instance và inbound TCP 22 từ IP nguồn. |
| SSH được nhưng API lỗi | Kiểm tra dịch vụ đang chạy, cổng và giao thức trong `baseURL`, Security Group và cấu hình CORS nếu chỉ lỗi trong trình duyệt. |

## Tài liệu liên quan

- [Mục lục tài liệu Examind](../README.md)
- [Xác minh fingerprint của instance EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connection-prereqs-general.html)
- [Kết nối EC2 bằng SSH](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-linux-inst-ssh.html)
- [Xử lý lỗi kết nối EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/TroubleshootingInstancesConnecting.html)
- [Dừng và khởi động lại EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Stop_Start.html)
