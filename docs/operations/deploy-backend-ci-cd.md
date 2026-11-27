# Deploy backend lên EC2 bằng GitHub Actions

Dành cho người merge vào `main` hoặc vận hành VPS demo. Mỗi lần merge đổi `backend/`, `deploy/` (kể cả cấu hình nginx), `docker-compose*.yml` thì GitHub Actions kiểm tra rồi tự deploy lên VPS. Thay đổi hai workflow backend kích hoạt CI trên PR. Nếu cần deploy lại sau khi sửa workflow, chạy workflow Deploy backend thủ công. Truy cập SSH và thông tin instance nằm ở [deploy-ec2.md](deploy-ec2.md).

## Điều kiện trước khi chạy

- Quyền ghi vào repo để merge. Quyền SSH và khoá `.pem` chỉ cần khi vận hành tay.
- Cổng **80** (HTTP, cũng dùng để Let's Encrypt xác minh tên miền) và **443** (HTTPS, WebSocket) mở trong Security Group của instance để truy cập API từ ngoài. Cổng 22 đã mở. Không mở 5432, 9000, 9001, 8000: các dịch vụ này chỉ nghe trên `127.0.0.1` của VPS.
- Tên miền `examind.duckdns.org` trỏ đúng Elastic IP (chứng chỉ chỉ cấp được khi tên miền về đúng VPS).
- Repo secrets đã tạo: `EC2_HOST` (hiện là Elastic IP `54.79.136.46`), `EC2_USER`, `EC2_SSH_KEY`, `EC2_KNOWN_HOSTS` (host key đã ghim, deploy dùng `StrictHostKeyChecking=yes`). Môi trường GitHub `production` được tạo tự động ở lần deploy đầu. Đặt secret ở **repo** (Settings → Secrets and variables → Actions), không đặt trùng tên trong environment `production`: secret của environment được ưu tiên hơn và dễ gây nhầm.

## Thông tin môi trường

| Mục | Giá trị |
| --- | --- |
| Thư mục trên VPS | `/opt/examind/app` (mã nguồn), `/opt/examind/seed` (gói dữ liệu nền), `/opt/examind/prod.env` (mật khẩu, chmod 600, không nằm trong Git) |
| Dịch vụ | `nginx` (cổng 80 và 443) → `backend` (FastAPI, nội bộ) → `postgres`, `minio`; `certbot` gia hạn chứng chỉ |
| Địa chỉ API | `https://examind.duckdns.org/api/v1/health` (và `http://` ở cổng 80). DuckDNS trỏ về Elastic IP `54.79.136.46`, IP không đổi khi dừng/khởi động instance, xem [deploy-ec2.md](deploy-ec2.md) |
| Địa chỉ socket | `wss://examind.duckdns.org/api/socket.io/` (nginx đã sẵn đường nâng cấp WebSocket, backend sẽ có ở issue #20) |
| Chứng chỉ HTTPS | Let's Encrypt, lưu ở `/opt/examind/letsencrypt`; thư mục thử thách ACME `/opt/examind/certbot-www`. Không nằm trong Git |
| Kiểm tra sống | `http://examind.duckdns.org/api/v1/health/live` trả `{"status":"ok","version":"0.1.0"}`, không chạm DB và MinIO |
| Workflow | [.github/workflows/ci.yml](../../.github/workflows/ci.yml), [.github/workflows/deploy.yml](../../.github/workflows/deploy.yml) |

## Luồng tự động

1. **PR vào `main` có thay đổi backend, hạ tầng hoặc workflow backend**: `ci.yml` chạy `pytest` backend, kiểm cú pháp Compose (dev và prod), build image backend, kiểm cú pháp nginx (`nginx -t`) và `bash -n` các script.
2. **Merge thay đổi backend hoặc hạ tầng vào `main`**: `deploy.yml` gọi lại `ci.yml` trên bản vừa merge. CI lỗi thì dừng, không deploy.
3. **Deploy** (`deploy/remote-deploy.sh` chạy trên VPS qua SSH):
   1. `git fetch` rồi `git reset --hard` về commit vừa merge.
   2. Chưa có chứng chỉ thì tạo bản tự ký tạm (để nginx khởi động được khối 443).
   3. `docker compose up -d --build`: dựng lại backend, chạy lại `db-init` (Alembic, một lần) và `minio-init`.
   4. `nginx -t` rồi `nginx -s reload` trong container nginx. Nhờ vậy sửa `deploy/nginx/conf.d/*` là có hiệu lực mà không cần dựng lại container.
   5. Gọi `http://127.0.0.1/api/v1/health` tối đa 2 phút. Lỗi thì in log, quay về commit trước, dựng lại và báo job thất bại.
   6. Lần đầu: xin chứng chỉ Let's Encrypt (`certbot certonly --webroot`), rồi reload nginx. Lỗi ở bước này chỉ cảnh báo, API vẫn chạy qua HTTP. Các lần sau bỏ qua; container `certbot` tự gia hạn và nginx tự nạp lại cấu hình mỗi 6 giờ.
   7. **Dọn Docker** (luôn chạy, kể cả khi lỗi): `docker image prune -f` (image dangling của các lần build cũ), `docker builder prune --keep-storage 1GB`. Không bao giờ dùng `--volumes`, vì `pgdata` và `miniodata` là dữ liệu thật.
4. Hai bước cuối gọi `http://<host>/api/v1/health` và `https://examind.duckdns.org/api/v1/health/live` từ runner để xác nhận cổng 80 và 443 mở ra ngoài, chứng chỉ hợp lệ.

Log Docker của mỗi container giới hạn 3 file × 10 MB.

## Sửa cấu hình nginx

1. Sửa `deploy/nginx/conf.d/` (`default.conf` cho khối server, `locations.inc` cho các location dùng chung cổng 80 và 443, `proxy.inc` cho header proxy) trên nhánh, mở PR. CI chạy `nginx -t` với chứng chỉ tự ký tạm.
2. Merge vào `main`: deploy tự chạy và reload nginx. Cấu hình lỗi thì `nginx -t` trên VPS dừng deploy và quay về bản trước.
3. Kiểm tra: `curl -i http://<host>/healthz` trả `200 ok`.

## Bootstrap VPS mới (một lần)

```bash
ssh -i ./backend-key.pem ubuntu@<host> 'bash -s' < deploy/bootstrap-vps.sh
```

Script cài Docker và Compose, thêm swap 2 GB (VPS chỉ có ~1,9 GB RAM), tạo `/opt/examind`, clone repo, sinh `prod.env` với mật khẩu ngẫu nhiên. Chạy lại an toàn. Việc nạp dữ liệu nền: [seed-base-data.md](seed-base-data.md).

## Biến trong prod.env

`/opt/examind/prod.env` (chmod 600, không nằm trong Git) được truyền vào compose bằng `--env-file`. `docker-compose.prod.yml` đưa các biến sau vào container:

| Biến | Container | Mặc định nếu thiếu | Ghi chú |
| --- | --- | --- | --- |
| `POSTGRES_PASSWORD`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | tất cả | bắt buộc (`:?`) | Sinh ngẫu nhiên khi bootstrap |
| `CORS_ORIGINS` | backend | `http://localhost:3000` | Chỉ cần khi frontend gọi thẳng backend khác origin |
| `COOKIE_SECURE` | backend, db-init | `true` | nginx có TLS. Cookie phiên chỉ gửi qua HTTPS; ở db-init bật luật mật khẩu admin ≥ 12 ký tự |
| `COOKIE_NAME` | backend | `examind_session` | |
| `SESSION_TTL_HOURS` | backend | `168` | Hạn phiên (giờ) |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME` | db-init | rỗng (bỏ qua admin mặc định) | `ensure_admin` tạo admin ở lần deploy kế tiếp nếu chưa có. Mật khẩu ≥ 12 ký tự, không chứa `$`. Đã có thì không đổi gì |

**VPS mới:** chạy bootstrap kèm email admin. Script sinh sẵn các biến trên, mật khẩu admin ngẫu nhiên khoảng 30 ký tự và không in ra màn hình:

```bash
ssh -i ./backend-key.pem ubuntu@<host> 'ADMIN_EMAIL=<email-admin> bash -s' < deploy/bootstrap-vps.sh
```

**VPS đang chạy:** cũng chạy lại lệnh trên. Script chỉ thêm biến còn thiếu, không đổi giá trị đã có. Hoặc thêm tay qua SSH:

1. `ssh -i ./backend-key.pem ubuntu@<host>`
2. `nano /opt/examind/prod.env`, thêm `COOKIE_SECURE=true`, `ADMIN_EMAIL=...`, `ADMIN_PASSWORD=...` (ngẫu nhiên, dài, vd `openssl rand -base64 24 | tr -d '$/+='`), `ADMIN_NAME=...`. Giữ `chmod 600`.
3. Merge hoặc chạy lại workflow Deploy backend. Kiểm admin đã tạo:

   ```bash
   cd /opt/examind/app && docker compose --env-file /opt/examind/prod.env -f docker-compose.yml -f docker-compose.prod.yml logs db-init | grep -i admin
   ```

   Mong đợi `Đã tạo admin mặc định ...` (lần đầu) hoặc `Admin mặc định đã có, không thay đổi`. Xem mật khẩu trên VPS: `grep '^ADMIN_PASSWORD=' /opt/examind/prod.env`. Không chép mật khẩu ra ngoài VPS ngoài nơi lưu trữ an toàn của nhóm.

Nếu `ADMIN_PASSWORD` dưới 12 ký tự hoặc sai định dạng, `db-init` thoát mã 2, backend không khởi động và deploy quay về commit trước. Email đã thuộc một tài khoản student thì chỉ cảnh báo trong log, không làm deploy fail. Cách thêm admin khác và cứu hộ: [backend-auth.md](../architecture/backend-auth.md#cấp-tài-khoản-admin).

## Kiểm tra kết quả

```bash
curl http://<host>/api/v1/health          # {"status":"ok","database":true,"storage":true}
curl http://<host>/api/v1/health/live     # {"status":"ok","version":"0.1.0"}
curl https://examind.duckdns.org/api/v1/health/live   # cùng kết quả, chứng chỉ hợp lệ (không dùng -k)
echo | openssl s_client -connect examind.duckdns.org:443 -servername examind.duckdns.org 2>/dev/null | openssl x509 -noout -issuer -enddate
curl -I http://<host>/docs                # 200, tài liệu API tự sinh
ssh ... 'cd /opt/examind/app && docker compose --env-file /opt/examind/prod.env -f docker-compose.yml -f docker-compose.prod.yml ps'
ssh ... 'docker system df; df -h /'
```

## Xử lý lỗi

| Triệu chứng | Nguyên nhân và cách xử lý |
| --- | --- |
| CI đỏ, job deploy bị bỏ qua | Đúng thiết kế. Sửa lỗi theo log CI rồi push lại |
| Bước "Kiểm tra từ bên ngoài" lỗi nhưng deploy trên VPS qua | Cổng 80 chưa mở trong Security Group |
| Bước "Kiểm tra HTTPS từ bên ngoài" lỗi, log deploy có "CẢNH BÁO: chưa xin được chứng chỉ" | Cổng 80 hoặc 443 chưa mở trong Security Group, hoặc DuckDNS trỏ sai IP. Sửa rồi chạy lại workflow Deploy backend (xin chứng chỉ tự thử lại). Let's Encrypt giới hạn 5 lần xác minh lỗi mỗi giờ |
| Trình duyệt báo chứng chỉ không tin cậy | Đang dùng chứng chỉ tự ký tạm: chưa xin được chứng chỉ thật. Xem dòng trên |
| Chứng chỉ sắp hết hạn | `docker compose ... logs certbot`; gia hạn thủ công: `docker compose ... run --rm --entrypoint certbot certbot renew --webroot -w /var/www/certbot` rồi `exec nginx nginx -s reload` |
| WebSocket ngắt sau vài giây | Qua nginx của VPS đã giữ 1 giờ (`locations.inc`). Nếu có proxy khác phía trước, kiểm tra timeout và header `Upgrade` |
| `Host key verification failed` | IP hoặc host key đổi. Lấy fingerprint mới từ AWS Console, cập nhật secrets `EC2_HOST` và `EC2_KNOWN_HOSTS` (lấy bằng `ssh-keyscan -T 10 <host>`, đối chiếu fingerprint trước khi lưu) |
| Tên miền không vào được nhưng IP vào được | DuckDNS đang trỏ sai IP. Vào duckdns.org, sửa ô current ip thành Elastic IP rồi bấm update ip |
| Deploy lỗi ở `health` rồi quay về bản cũ | Xem `compose logs backend` trong log job; sửa rồi merge lại |
| Build chậm hoặc bị kill (OOM) | Kiểm `free -m` có swap; không chạy hai deploy cùng lúc (workflow đã dùng `concurrency`) |
| Đầy ổ đĩa | `docker system df`; chạy `docker builder prune -af` và `docker image prune -af`; không xoá volume |

## Tài liệu liên quan

- [Truy cập VPS](deploy-ec2.md)
- [Nạp dữ liệu nền](seed-base-data.md)
- [Chạy bộ khung local](run-local-stack.md)
