# Nạp dữ liệu nền (câu hỏi, đề, ảnh)

Dành cho người dựng hoặc cập nhật dữ liệu nền từ bản backup của hệ thống cũ (MySQL + MinIO), ở máy nhóm và trên VPS. Gói dữ liệu **chỉ gồm bảng nội dung và ảnh được nội dung tham chiếu**; không có người dùng, học sinh, phụ huynh, thanh toán, token hay `exam_import_sessions`.

## Điều kiện trước khi chạy

- Thư mục backup (`mysql.sql.gz`, `minio-objects.tar.gz`, `SHA256SUMS`) đặt trong `data/private/`. Thư mục này nằm trong `.gitignore`; không commit, không đưa vào image Docker.
- Docker, Python 3.12, `pip install -r backend/requirements-seed.txt`.
- Chạy lệnh ở thư mục gốc repo.

## Các bước thực hiện

1. Kiểm backup: `cd data/private/<thư-mục-backup> && sha256sum -c SHA256SUMS`.
2. Dựng gói dữ liệu (khoảng vài phút; quét 3,7 GB tar):

   ```bash
   python backend/scripts/build_seed.py --backup data/private/<thư-mục-backup> --out data/private/seed
   ```

   Script chạy MySQL tạm trên tmpfs, chỉ xuất các bảng trong `ALLOWED_TABLES` ra `content/*.csv`, ghi `NULL` vào cột trỏ tới người dùng (`created_by`, `uploaded_by`, `folder_id`) và `media.raw_content`, rồi lấy từ tar đúng các đối tượng MinIO mà `media` được nội dung tham chiếu (`![media:ID](media:ID)`). Kết quả `content/manifest.json` ghi số dòng và số đối tượng thiếu.
3. Local: `docker compose up -d`. Hai container init đọc `data/private/seed` (đổi bằng biến `SEED_DIR`):
   - `db-init`: `alembic upgrade head`, rồi `scripts/seed_load.py` nạp CSV trong một giao dịch và ghi dấu `base_seed` vào `app_init_state`.
   - `minio-init`: tạo bucket, `mc mirror` ảnh, ghi dấu `examind/.init/base-seed`.
4. VPS: đưa gói lên `/opt/examind/seed` (bước này đã làm một lần), rồi deploy bình thường:

   ```bash
   tar -C data/private/seed -cf - . | ssh -i ./backend-key.pem ubuntu@<host> 'tar -C /opt/examind/seed -xf - && chmod -R go-rwx /opt/examind/seed'
   ```

**Nạp một lần:** có dấu `base_seed` (PostgreSQL) hoặc `.init/base-seed` (MinIO) thì lần chạy sau bỏ qua. Muốn nạp lại thì xoá dấu tương ứng hoặc `docker compose down -v` (xoá cả dữ liệu).

## Kiểm tra kết quả

Đã kiểm ngày 27/11/2026 trên máy local và VPS:

| Mục | Kết quả |
| --- | --- |
| Số dòng | `subjects` 8 · `chapters` 104 · `questions` 14.146 · `statements` 42.286 · `questions_chapters` 15.753 · `exams` 621 · `sections` 1.799 · `questions_exams` 14.088 · `media` 5.405 |
| Ảnh | 5.405 đối tượng (260 MB), mọi dòng `media` có đối tượng tương ứng trong MinIO, không thiếu cái nào |
| Ảnh thật | Đọc một đối tượng PNG, đúng chữ ký `89 50 4E 47` |
| Chạy lại init | Log `Đã nạp ... bỏ qua`, không nạp trùng |
| Bảng cá nhân | Không có `users`, `students`, `parents`, `exam_import_sessions` trong PostgreSQL |

Lệnh kiểm nhanh:

```bash
docker compose exec postgres psql -U examind -d examind -c "select count(*) from questions"
```

## Xử lý lỗi

| Triệu chứng | Cách xử lý |
| --- | --- |
| `build_seed.py` báo thiếu đối tượng | Xem `objects_missing` trong `content/manifest.json`; tar backup thiếu tệp đó |
| `db-init` lỗi `nạp N dòng, gói có M` | Giao dịch tự huỷ, chưa có dấu; sửa gói rồi chạy lại `docker compose up -d` |
| Muốn thêm bảng vào gói | Thêm tên bảng vào `ALLOWED_TABLES` (build_seed.py), thêm migration và danh sách `IDENTITY` (seed_load.py). Không thêm bảng chứa dữ liệu cá nhân |

## Giới hạn

- Schema `0002_base_content` phản chiếu hệ thống cũ làm nền; các issue #3, #4, #5 mở rộng bằng migration riêng.
- Migration `0021_questions_archived_at` (#11) thêm cột `questions.archived_at` (NULL). Gói dữ liệu nền không có cột này nên mọi câu nạp vào đều chưa lưu trữ. Câu khả dụng cho đề mới là `visibility = 'PUBLISHED'` và `archived_at IS NULL`, xem [API quản lý ngân hàng câu hỏi](../api/admin-data-api.md).
- Gói dữ liệu là bản chụp ngày dựng, không đồng bộ liên tục với hệ thống cũ.
- Ảnh trên VPS chưa có URL công khai; truy cập qua backend (presigned URL) ở issue sau.

## Tài liệu liên quan

- [Deploy backend bằng GitHub Actions](deploy-backend-ci-cd.md)
- [Chạy bộ khung local](run-local-stack.md)
- [Data card](../../data/DATA_CARD.md)
