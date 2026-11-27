# Deploy backend lên EC2 bằng GitHub Actions

Dành cho người merge vào `main` hoặc vận hành VPS demo. Mỗi lần merge đổi `backend/`, `deploy/` (kể cả cấu hình nginx), `docker-compose*.yml` hoặc hai workflow, GitHub Actions kiểm tra rồi tự deploy lên VPS. Truy cập SSH và thông tin instance nằm ở [deploy-ec2.md](deploy-ec2.md).

## Điều kiện trước khi chạy

- Quyền ghi vào repo để merge. Quyền SSH và khoá `.pem` chỉ cần khi vận hành tay.
- Cổng **80** (HTTP) mở trong Security Group của instance để truy cập API từ ngoài. Cổng 22 đã mở. Không mở 5432, 9000, 9001, 8000: các dịch vụ này chỉ nghe trên `127.0.0.1` của VPS.
- Repo secrets đã tạo: `EC2_HOST` (hiện là Elastic IP `54.79.136.46`), `EC2_USER`, `EC2_SSH_KEY`, `EC2_KNOWN_HOSTS` (host key đã ghim, deploy dùng `StrictHostKeyChecking=yes`). Môi trường GitHub `production` được tạo tự động ở lần deploy đầu. Đặt secret ở **repo** (Settings → Secrets and variables → Actions), không đặt trùng tên trong environment `production`: secret của environment được ưu tiên hơn và dễ gây nhầm.

## Thông tin môi trường

| Mục | Giá trị |
| --- | --- |
| Thư mục trên VPS | `/opt/examind/app` (mã nguồn), `/opt/examind/seed` (gói dữ liệu nền), `/opt/examind/prod.env` (mật khẩu, chmod 600, không nằm trong Git) |
| Dịch vụ | `nginx` (cổng 80) → `backend` (FastAPI, nội bộ) → `postgres`, `minio` |
| Địa chỉ API | `http://examind.duckdns.org/api/v1/health` (DuckDNS trỏ về Elastic IP `54.79.136.46`, IP không đổi khi dừng/khởi động instance, xem [deploy-ec2.md](deploy-ec2.md)) |
| Kiểm tra sống | `http://examind.duckdns.org/api/v1/health/live` trả `{"status":"ok","version":"0.1.0"}`, không chạm DB và MinIO |
| Workflow | [.github/workflows/ci.yml](../../.github/workflows/ci.yml), [.github/workflows/deploy.yml](../../.github/workflows/deploy.yml) |

## Luồng tự động

1. **PR vào `main`**: `ci.yml` chạy `pytest` backend, kiểm cú pháp Compose (dev và prod), build image backend, kiểm cú pháp nginx (`nginx -t`) và `bash -n` các script.
2. **Merge vào `main`**: `deploy.yml` gọi lại `ci.yml` trên bản vừa merge. CI lỗi thì dừng, không deploy.
3. **Deploy** (`deploy/remote-deploy.sh` chạy trên VPS qua SSH):
   1. `git fetch` rồi `git reset --hard` về commit vừa merge.
   2. `docker compose up -d --build`: dựng lại backend, chạy lại `db-init` (Alembic, một lần) và `minio-init`.
   3. `nginx -t` rồi `nginx -s reload` trong container nginx. Nhờ vậy sửa `deploy/nginx/conf.d/default.conf` là có hiệu lực mà không cần dựng lại container.
   4. Gọi `http://127.0.0.1/api/v1/health` tối đa 2 phút. Lỗi thì in log, quay về commit trước, dựng lại và báo job thất bại.
   5. **Dọn Docker** (luôn chạy, kể cả khi lỗi): `docker image prune -f` (image dangling của các lần build cũ), `docker builder prune --keep-storage 1GB`. Không bao giờ dùng `--volumes`, vì `pgdata` và `miniodata` là dữ liệu thật.
4. Job cuối gọi `http://<host>/api/v1/health` từ runner để xác nhận cổng 80 mở ra ngoài.

Log Docker của mỗi container giới hạn 3 file × 10 MB.

## Sửa cấu hình nginx

1. Sửa `deploy/nginx/conf.d/default.conf` trên nhánh, mở PR. CI chạy `nginx -t`.
2. Merge vào `main`: deploy tự chạy và reload nginx. Cấu hình lỗi thì `nginx -t` trên VPS dừng deploy và quay về bản trước.
3. Kiểm tra: `curl -i http://<host>/healthz` trả `200 ok`.

## Bootstrap VPS mới (một lần)

```bash
ssh -i ./backend-key.pem ubuntu@<host> 'bash -s' < deploy/bootstrap-vps.sh
```

Script cài Docker và Compose, thêm swap 2 GB (VPS chỉ có ~1,9 GB RAM), tạo `/opt/examind`, clone repo, sinh `prod.env` với mật khẩu ngẫu nhiên. Chạy lại an toàn. Việc nạp dữ liệu nền: [seed-base-data.md](seed-base-data.md).

## Kiểm tra kết quả

```bash
curl http://<host>/api/v1/health          # {"status":"ok","database":true,"storage":true}
curl http://<host>/api/v1/health/live     # {"status":"ok","version":"0.1.0"}
curl -I http://<host>/docs                # 200, tài liệu API tự sinh
ssh ... 'cd /opt/examind/app && docker compose --env-file /opt/examind/prod.env -f docker-compose.yml -f docker-compose.prod.yml ps'
ssh ... 'docker system df; df -h /'
```

## Xử lý lỗi

| Triệu chứng | Nguyên nhân và cách xử lý |
| --- | --- |
| CI đỏ, job deploy bị bỏ qua | Đúng thiết kế. Sửa lỗi theo log CI rồi push lại |
| Bước "Kiểm tra từ bên ngoài" lỗi nhưng deploy trên VPS qua | Cổng 80 chưa mở trong Security Group |
| `Host key verification failed` | IP hoặc host key đổi. Lấy fingerprint mới từ AWS Console, cập nhật secrets `EC2_HOST` và `EC2_KNOWN_HOSTS` (lấy bằng `ssh-keyscan -T 10 <host>`, đối chiếu fingerprint trước khi lưu) |
| Tên miền không vào được nhưng IP vào được | DuckDNS đang trỏ sai IP. Vào duckdns.org, sửa ô current ip thành Elastic IP rồi bấm update ip |
| Deploy lỗi ở `health` rồi quay về bản cũ | Xem `compose logs backend` trong log job; sửa rồi merge lại |
| Build chậm hoặc bị kill (OOM) | Kiểm `free -m` có swap; không chạy hai deploy cùng lúc (workflow đã dùng `concurrency`) |
| Đầy ổ đĩa | `docker system df`; chạy `docker builder prune -af` và `docker image prune -af`; không xoá volume |

## Tài liệu liên quan

- [Truy cập VPS](deploy-ec2.md)
- [Nạp dữ liệu nền](seed-base-data.md)
- [Chạy bộ khung local](run-local-stack.md)
