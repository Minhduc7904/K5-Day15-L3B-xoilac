# Kiến trúc frontend Examind

Dành cho người phát triển bộ khung frontend. Bộ khung dùng App Router, TypeScript, Tailwind CSS, Redux Toolkit và Axios.

## Bối cảnh và ràng buộc

Frontend nằm trong `frontend/` và build độc lập với FastAPI. Hai route có entry point riêng cho học sinh và quản trị, dùng chung metadata trình duyệt, font, token và splash khởi động. Mỗi khu tự đặt header của mình. Giao diện nghiệp vụ sẽ được phát triển trong từng route.

## Thành phần và trách nhiệm

| Vị trí trong `frontend/src/` | Trách nhiệm |
| --- | --- |
| `app/(student)/page.tsx` | Entry point `/`. Hiện render landing page cho khách (`features/landing/`). Route group giữ thư mục riêng và giữ URL gốc |
| `app/admin/page.tsx`, `app/admin/layout.tsx` | Entry point `/admin` cho quản trị, header có logo |
| `app/(auth)/` | Trang `/login`, `/register`, `/forgot-password`, `/verify-otp`, `/reset-password` (đang chạy mock). Xem [Trang xác thực frontend](frontend-auth.md) |
| `features/auth/` | Lớp API auth (mock hoặc Axios), reducer `auth`, form và validation |
| `app/design-system/page.tsx` | Trang xem thử token và component, chỉ bật ở dev hoặc chế độ mock |
| `app/layout.tsx` | Layout gốc: font, favicon, metadata và `AppProvider` |
| `components/ui/`, `components/layout/`, `components/motion/` | Component dùng chung, xem [Design system frontend](frontend-design-system.md) |
| `components/splash/`, `lib/bootstrap.ts` | Splash và các bước khởi động app |
| `app/globals.css` | Token màu, thang chữ và font stack dùng chung. Xem [Design system frontend](frontend-design-system.md) |
| `app/manifest.ts` | Manifest web với tên, màu và icon ứng dụng |
| `../public/brand/` | Logo chữ WebP, biểu tượng PNG và các cỡ icon cho trình duyệt |
| `store/index.ts` | Khởi tạo Redux store với reducer `auth` và cung cấp hook có kiểu |
| `store/provider.tsx` | Bọc app bằng Redux, `MotionConfig`, `ToastProvider` và `SplashScreen` |
| `lib/config.ts` | Cấu hình công khai, gồm base URL và cờ chế độ mock |
| `lib/api-client.ts` | Axios client dùng chung với base URL và timeout |

## Luồng dữ liệu và tích hợp

Khi thêm chức năng, đặt component, hook và adapter dữ liệu của từng feature gần nhau. Thành phần hiển thị gọi hook. Adapter của feature dùng Axios khi gọi backend. Đăng ký reducer của feature vào store khi cần chia sẻ trạng thái. Repo có cờ cấu hình để nối mock ở mốc tiếp theo.

## Font, màu và thang chữ

Dùng font Be Vietnam Pro qua `font-sans` và chỉ dùng màu từ token như `bg-primary`, `text-muted-foreground`. Không dùng mã hex hay class màu mặc định của Tailwind. Chi tiết và bảng tương phản ở [Design system frontend](frontend-design-system.md).

## Logo và icon

Dùng `/brand/examind-logo.webp` cho logo chữ và `/brand/examind-mark.png` khi cần biểu tượng vuông trong giao diện. Favicon, Apple Touch Icon và icon manifest lấy từ cùng biểu tượng gốc.

Import từng icon Lucide trong component cần dùng. Với nút chỉ có icon, đặt nhãn trên nút để trình đọc màn hình đọc được hành động.

```tsx
import { BookOpen } from 'lucide-react';

<button type="button" aria-label="Mở tài liệu">
  <BookOpen size={20} aria-hidden="true" />
</button>
```

## Linh vật và trạng thái chờ

- `frontend/public/brand/mascot/running/` có 8 khung chạy cho màn hình tải. `app/loading.tsx` hiển thị linh vật khi Next.js đang chờ route. Các route đã sẵn sàng hiển thị ngay.
- `frontend/public/brand/mascot/thinking/` có 8 khung suy nghĩ. Trong giao diện chat, render `<AgentThinking active={isAwaitingReply} />` từ `@/components/mascot/agent-thinking`. Đặt cờ khi gửi yêu cầu và tắt khi nhận phần phản hồi đầu tiên, yêu cầu lỗi hoặc bị hủy.
- Mỗi thư mục hoạt ảnh có 8 tệp `frame-*.webp` trong suốt 256 × 256 và một `loop.webp` chứa cùng các khung theo thứ tự. Mỗi khung chạy kéo dài 105 ms, mỗi khung suy nghĩ kéo dài 520 ms. Component dùng khung đầu khi thiết bị bật `prefers-reduced-motion`.
- `frontend/public/brand/mascot/static/` có 8 ảnh WebP trong suốt 384 × 384. Bộ góc nhìn gồm `front.webp`, `left.webp`, `back.webp`, `right.webp`. Bộ tư thế gồm `welcome.webp`, `working.webp`, `success.webp`, `studying.webp`. Dùng đường dẫn `/brand/mascot/static/<tên-tệp>` với `next/image`.
- Kiểm thử bằng route có nội dung tải bất đồng bộ và trạng thái chat mô phỏng. Kiểm tra nhãn chờ, 8 khung của mỗi vòng lặp và ảnh tĩnh ở chế độ giảm chuyển động.


## Quyết định và cách kiểm chứng

Dùng `npm run typecheck` và `npm run build` trong `frontend/`. Sau khi chạy `npm run start`, `/`, `/admin`, các trang auth và `/design-system` (khi bật chế độ mock) trả HTTP 200. Endpoint mẫu để kiểm tra Axios là `GET /health` tương đối với base URL chứa `/api/v1`.

## Tài liệu liên quan

- [Đặc tả sản phẩm](../../spec.md)
- [Design system frontend](frontend-design-system.md)
- [Trang xác thực frontend](frontend-auth.md)
- [API mẫu](../api/sample-api.md)
- [Chạy và triển khai frontend](../operations/deploy-frontend-vercel.md)
- [Issue #9](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/9)
