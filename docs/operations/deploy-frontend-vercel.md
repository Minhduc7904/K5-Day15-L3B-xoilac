# Chạy và triển khai frontend Examind lên Vercel

Dành cho thành viên chạy bộ khung frontend local hoặc cấu hình project Vercel khi nhóm chuẩn bị triển khai.

## Điều kiện trước khi chạy

- Node.js 22 và npm.
- Tài khoản Vercel có quyền import repo GitHub của nhóm khi liên kết project.
- Khi gọi API từ một frontend HTTPS, dùng base URL HTTPS và cấu hình CORS cho origin tương ứng.

## Thông tin môi trường

| Biến | Giá trị |
| --- | --- |
| `NEXT_PUBLIC_MOCK_MODE` | Mặc định `true`. Cờ để các feature dùng khi có adapter mock |
| `NEXT_PUBLIC_API_BASE_URL` | Base URL bao gồm `/api/v1`, mặc định `http://localhost:8000/api/v1` |

Các biến `NEXT_PUBLIC_*` được đưa vào bundle trình duyệt. Tạo deployment mới sau khi đổi giá trị.

## Các bước thực hiện

### Chạy local

```powershell
cd frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Mở `http://localhost:3000/` và `http://localhost:3000/admin`. Cả hai trang hiển thị logo ở header.

### CI và deploy tự động

- [CI frontend](../../.github/workflows/frontend-ci.yml) chạy `npm ci`, `npm run typecheck` và `npm run build` trên Node.js 22 khi PR vào `main` hoặc push lên `main` đổi `frontend/` hay workflow CI frontend.
- Project Vercel `examind-frontend` kết nối repo GitHub. Root Directory là `frontend`, preset là Next.js, Node.js là 22.x và nhánh Production là `main`. Vercel tạo Preview từ nhánh tính năng có thay đổi frontend và deploy Production từ `main`.
- [Ignored Build Step](../../frontend/vercel.json) so sánh phần `frontend/` với commit đã deploy thành công gần nhất. Preview đầu tiên trên nhánh mới so với điểm tách từ `main`. Nếu thiếu mốc so sánh, Vercel chạy build để giữ bản đang phục vụ đồng bộ. Lần deploy Git đầu tiên trên `main` tạo mốc cho Production.
- Kiểm tra CI frontend và Preview trước khi merge. Khi cần quay lui, chọn một deployment trước đó trên Vercel.

## Kiểm tra kết quả

Trong `frontend/`, chạy `npm run typecheck` và `npm run build`. Kết quả build liệt kê `/` và `/admin`. Chạy `npm run start` rồi kiểm HTTP 200 trên cả hai route. Sau deploy, kiểm tra mục Deployments trên Vercel và xác nhận commit khớp với nhánh vừa push. [Route học sinh](https://examind-frontend.vercel.app/) và [route quản trị](https://examind-frontend.vercel.app/admin) phải trả HTTP 200.

## Xử lý lỗi

| Triệu chứng | Kiểm tra |
| --- | --- |
| Vercel không tìm thấy Next.js | Kiểm tra Root Directory là `frontend` |
| `npm ci` hoặc build lỗi | Kiểm tra Node.js 22 và lockfile |
| API thật báo lỗi mạng khi tích hợp | Kiểm tra base URL, HTTPS và CORS |

## Tài liệu liên quan

- [Kiến trúc frontend](../architecture/frontend-base.md)
- [API mẫu](../api/sample-api.md)
- [Thiết lập Vercel cho coding agent](https://vercel.com/get-started.md)
- [Triển khai từ GitHub trên Vercel](https://vercel.com/docs/git)
