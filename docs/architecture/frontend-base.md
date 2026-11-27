# Kiến trúc frontend Examind

Dành cho người phát triển bộ khung frontend. Bộ khung dùng App Router, TypeScript, Tailwind CSS, Redux Toolkit và Axios.

## Bối cảnh và ràng buộc

Frontend nằm trong `frontend/` và build độc lập với FastAPI. Hai route có entry point riêng để phát triển giao diện học sinh và quản trị. Cả hai route dùng chung header logo và metadata trình duyệt. Giao diện nghiệp vụ sẽ được phát triển trong từng route.

## Thành phần và trách nhiệm

| Vị trí trong `frontend/src/` | Trách nhiệm |
| --- | --- |
| `app/(student)/page.tsx` | Entry point `/` cho học sinh. Route group giữ thư mục riêng và giữ URL gốc |
| `app/admin/page.tsx` | Entry point `/admin` cho quản trị |
| `app/layout.tsx` | Layout, logo, favicon và Redux provider dùng chung |
| `app/manifest.ts` | Manifest web với tên, màu và icon ứng dụng |
| `../public/brand/` | Logo chữ WebP, biểu tượng PNG và các cỡ icon cho trình duyệt |
| `store/index.ts` | Khởi tạo Redux store và cung cấp hook có kiểu |
| `lib/config.ts` | Cấu hình công khai, gồm base URL và cờ chế độ mock |
| `lib/api-client.ts` | Axios client dùng chung với base URL và timeout |

## Luồng dữ liệu và tích hợp

Khi thêm chức năng, đặt component, hook và adapter dữ liệu của từng feature gần nhau. Thành phần hiển thị gọi hook. Adapter của feature dùng Axios khi gọi backend. Đăng ký reducer của feature vào store khi cần chia sẻ trạng thái. Repo có cờ cấu hình để nối mock ở mốc tiếp theo.

## Logo và icon

Dùng `/brand/examind-logo.webp` cho logo chữ và `/brand/examind-mark.png` khi cần biểu tượng vuông trong giao diện. Favicon, Apple Touch Icon và icon manifest lấy từ cùng biểu tượng gốc.

Import từng icon Lucide trong component cần dùng. Với nút chỉ có icon, đặt nhãn trên nút để trình đọc màn hình đọc được hành động.

```tsx
import { BookOpen } from 'lucide-react';

<button type="button" aria-label="Mở tài liệu">
  <BookOpen size={20} aria-hidden="true" />
</button>
```

## Quyết định và cách kiểm chứng

Dùng `npm run typecheck` và `npm run build` trong `frontend/`. Sau khi chạy `npm run start`, cả `/` và `/admin` trả HTTP 200. Endpoint mẫu để kiểm tra Axios là `GET /health` tương đối với base URL chứa `/api/v1`.

## Tài liệu liên quan

- [Đặc tả sản phẩm](../../spec.md)
- [API mẫu](../api/sample-api.md)
- [Chạy và triển khai frontend](../operations/deploy-frontend-vercel.md)
- [Issue #9](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/9)
