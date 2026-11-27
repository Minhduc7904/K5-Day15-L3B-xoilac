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

### Cấu hình Vercel

1. Trên dashboard Vercel, chọn **Add New → Project** và import repo GitHub.
2. Đặt **Root Directory** thành `frontend`, chọn preset **Next.js** và Node.js **22.x**.
3. Cài biến môi trường theo bảng trên. Với project mới, Vercel CLI yêu cầu deployment đầu tiên ở Production. Khi nhóm đã đồng ý phát hành lần đầu, dùng Preview cho các nhánh tiếp theo và kiểm tra hai route trước khi cập nhật Production.
4. Nếu cần quay lui, chọn một deployment trước đó theo quy trình của project Vercel.

## Kiểm tra kết quả

Trong `frontend/`, chạy `npm run typecheck` và `npm run build`. Kết quả build liệt kê `/` và `/admin`. Chạy `npm run start` rồi kiểm HTTP 200 trên cả hai route. Ngày 27/11/2026, bản scaffold được deploy từ thư mục `frontend/` bằng `vercel deploy --prod`. [Route học sinh](https://examind-frontend.vercel.app/) và [route quản trị](https://examind-frontend.vercel.app/admin) đều trả HTTP 200. Bản deploy này dùng Vercel CLI. Tự động deploy từ GitHub cần kết nối repo với project.

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
