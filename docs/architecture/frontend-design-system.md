# Design system frontend Examind

Dành cho người viết giao diện trong `frontend/`. Tài liệu này ghi font, thang chữ, token màu, bộ component dùng chung, thư viện hiệu ứng và splash khởi động, dùng cho landing, auth và các màn hình sau này ([issue #16](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/16)). Xem trực tiếp mọi token và component tại route `/design-system` khi chạy `npm run dev`.

## Bối cảnh và ràng buộc

- Màu lấy từ logo có sẵn trong `frontend/public/brand/`. Issue #16 không làm logo mới.
- Dự án chỉ dùng **một** họ font, có đủ dấu tiếng Việt, cấu hình một lần bằng `next/font`.
- Toàn bộ code trong `frontend/src/` chỉ dùng màu từ token. Không dùng mã hex hay class màu mặc định của Tailwind (`slate-*`, `cyan-*`…).
- Màu chữ trên nền đạt WCAG AA 4.5:1. Viền ô nhập, vòng focus và thành phần không phải chữ đạt 3:1.

## Thành phần và trách nhiệm

| Vị trí | Trách nhiệm |
| --- | --- |
| `frontend/src/app/globals.css` | Nguồn duy nhất của token màu, thang chữ và font stack, khai báo bằng `@theme` của Tailwind v4. Style nền của `body`, focus và vùng chọn chữ |
| `frontend/src/app/layout.tsx` | Nạp font Be Vietnam Pro bằng `next/font/google` và gắn biến `--font-be-vietnam-pro` vào `<html>` |
| `frontend/src/app/manifest.ts`, `viewport` trong `layout.tsx` | `background_color`, `theme_color` và `themeColor` chép tay từ token `background` và `foreground` vì không đọc được biến CSS |
| `frontend/src/components/ui/` | Component nguyên tố dùng chung, không phụ thuộc feature |
| `frontend/src/components/layout/` | `Container`, `Section`, `SectionHeader`, `Logo`, `Navbar`, `Footer` |
| `frontend/src/components/motion/reveal.tsx` | Hiệu ứng dùng chung: `Reveal`, `Stagger`, `StaggerItem`, `Float` |
| `frontend/src/components/splash/splash-screen.tsx`, `lib/bootstrap.ts` | Splash khởi động và danh sách bước khởi động |
| `frontend/src/store/provider.tsx` | Bọc app bằng Redux, `MotionConfig`, `ToastProvider` và `SplashScreen` |
| `frontend/src/features/landing/` | Landing page tại `/` |
| `frontend/src/features/design-system/`, `app/design-system/page.tsx` | Trang xem thử token và component, chỉ bật ở dev hoặc `NEXT_PUBLIC_MOCK_MODE` khác `false` |

### Component dùng chung

Mọi component có kiểu TypeScript, dùng được bằng bàn phím, có vòng focus `ring` và chỉ dùng token màu.

| Component | File | Biến thể và trạng thái |
| --- | --- | --- |
| `Button` | `ui/button.tsx` | `primary`, `secondary`, `outline`, `ghost`, `accent`, `danger`, `inverse` (trên nền tối); cỡ `sm`, `md`, `lg`; `loading` (spinner + `aria-busy`), `disabled`, `leftIcon`, `rightIcon`, `fullWidth`; truyền `href` để thành link |
| `IconButton` | `ui/button.tsx` | `ghost`, `outline`, `secondary`, `primary`; prop `label` bắt buộc, gắn vào `aria-label` |
| `Input`, `Textarea` | `ui/input.tsx` | `invalid`, `disabled`, `leftIcon`, `rightSlot` |
| `PasswordInput` | `ui/password-input.tsx` | Nút hiện/ẩn có nhãn "Hiện mật khẩu"/"Ẩn mật khẩu" và `aria-pressed` |
| `Label`, `FormField` | `ui/form-field.tsx` | Nhãn, dấu bắt buộc, gợi ý, lỗi có hoạt ảnh; `FormField` truyền `id`, `invalid`, `aria-describedby` cho ô nhập qua render-prop |
| `Checkbox`, `Switch` | `ui/checkbox.tsx` | Checkbox native tự vẽ, có mô tả và trạng thái lỗi; Switch `role="switch"` có hoạt ảnh lò xo |
| `Alert` | `ui/feedback.tsx` | `info`, `success`, `warning`, `danger`; tiêu đề, nội dung, `action`, `onDismiss`. Cảnh báo và lỗi dùng `role="alert"` |
| `Badge`, `Skeleton` | `ui/feedback.tsx` | Badge 7 tông, có `dot` hoặc `icon`; Skeleton có ánh chạy |
| `Spinner` | `ui/spinner.tsx` | `sm`, `md`, `lg`; có `label` thì tự báo trạng thái |
| `Toast` | `ui/toast.tsx` | `useToast()` trả hàm `toast({ title, description, tone, duration })`, vùng `aria-live`, tự ẩn |
| `Card` và phần con | `ui/card.tsx` | `default`, `muted`, `elevated`, `outline`; `interactive` nổi lên khi rê chuột |
| `Accordion`, `Tabs`, `Progress` | `ui/interactive.tsx` | Accordion mở bằng hoạt ảnh chiều cao; Tabs theo mẫu WAI-ARIA (mũi tên, Home, End); Progress có `role="progressbar"` |

Ví dụ một trường trong biểu mẫu:

```tsx
<FormField label="Email" required hint="Dùng email bạn đăng ký." error={errors.email}>
  {(field) => <Input {...field} type="email" autoComplete="email" leftIcon={<Mail />} />}
</FormField>
```

### Hiệu ứng

Dùng thư viện **Motion** (`motion@14.14.0`, import từ `motion/react`) cho hoạt ảnh có trạng thái: xuất hiện khi cuộn, stagger, lơ lửng, accordion, tab, toast, splash. Hoạt ảnh lặp đơn giản dùng CSS qua token `animate-marquee`, `animate-twinkle`, `animate-shimmer` trong `globals.css`.

- `AppProvider` bọc app bằng `<MotionConfig reducedMotion="user">`, nên khi hệ điều hành bật giảm chuyển động thì Motion bỏ chuyển động trượt. `globals.css` cũng rút ngắn hoạt ảnh CSS trong trường hợp này, và `MascotAnimation` dùng khung tĩnh.
- Dùng `Reveal` cho một khối, `Stagger` + `StaggerItem` cho danh sách, `Float` cho hình minh hoạ. Không tự viết `initial/whileInView` lặp lại trong từng trang.

### Splash khởi động

`SplashScreen` phủ toàn màn hình khi tải trang, hiện linh vật `running`, logo, thanh tiến độ và tên bước đang chạy. Các bước nằm trong `bootstrapSteps` ở `lib/bootstrap.ts`, chạy lần lượt, mỗi bước tối đa 4 giây để splash không treo. Hiện có ba bước: chờ font, nạp sẵn ảnh linh vật, và kiểm tra phiên đăng nhập (**đang giả lập**, sẽ nối API của #8). Lần đầu trong phiên trình duyệt splash hiện ít nhất 1,6 giây, các lần tải lại 0,5 giây. Nội dung phía sau bị `inert` cho tới khi splash tắt. Khi trình duyệt tắt JavaScript, thẻ `<noscript>` trong `layout.tsx` ẩn splash. `app/loading.tsx` vẫn dùng linh vật cho trạng thái chờ khi chuyển route.

### Landing page

Landing đặt ở `/` (`app/(student)/page.tsx` render `LandingPage`). Khi có phiên thật (#8), học sinh đã đăng nhập sẽ được chuyển vào khu học tập. Các khối: hero với khung chat minh hoạ tự chạy, dải chương lớp 10–12 (tên lấy từ `data/chapters.csv`), vấn đề, cách hoạt động, điểm nổi bật, những điều Examind không làm, hỏi đáp, kêu gọi cuối trang, footer. Nội dung bám `spec.md` §4. Số liệu trong khung chat và biểu đồ chương được ghi rõ là ví dụ. Nút Đăng nhập và Tạo tài khoản hiện chỉ báo bằng toast, chưa chuyển trang.

### Font chữ

Dùng **Be Vietnam Pro** cho toàn dự án.

- Lý do: font được thiết kế riêng cho tiếng Việt nên dấu chồng (ệ, ẫ, Ỗ) đặt đúng vị trí và không va dòng trên. Dáng geometric sans gần với chữ "Examind" trong logo. Chữ số rõ ràng, phân biệt được `1`, `l`, `I` khi hiển thị công thức Toán ngắn như `x² + 2x − 3 = 0`.
- Độ đậm dùng: 400 (đoạn văn), 500 (nhãn, nút), 600 (tiêu đề phụ), 700 (tiêu đề chính).
- Subset: `latin`, `vietnamese`. `display: swap`.
- Font dự phòng: `ui-sans-serif, system-ui, "Segoe UI", Roboto, Arial, sans-serif`.
- Tailwind dùng qua `font-sans`. Đây cũng là font mặc định của trang vì preflight của Tailwind lấy `--font-sans`.

Không nhúng font ở nơi khác và không thêm họ font thứ hai. Khi cần số thẳng cột trong bảng điểm, dùng `tabular-nums` thay vì đổi font.

### Thang chữ

Mỗi bậc là một utility `text-<tên>` đã gồm cỡ chữ, chiều cao dòng, độ đậm và khoảng cách chữ. Tiêu đề giữ chiều cao dòng từ 1.15 trở lên để dấu tiếng Việt không bị cắt.

| Utility | Cỡ chữ | Chiều cao dòng | Độ đậm | Dùng cho |
| --- | --- | --- | --- | --- |
| `text-display` | 36 → 56px (co theo màn hình) | 1.15 | 700 | Tiêu đề hero landing |
| `text-h1` | 30 → 40px | 1.25 | 700 | Tiêu đề trang |
| `text-h2` | 24 → 30px | 1.3 | 600 | Tiêu đề khối |
| `text-h3` | 20px | 1.4 | 600 | Tiêu đề thẻ, nhóm |
| `text-body-lg` | 18px | 1.65 | 400 | Đoạn mở đầu, mô tả hero |
| `text-body` | 16px | 1.6 | 400 | Đoạn văn mặc định của `body` |
| `text-label` | 14px | 1.45 | 500 | Nhãn ô nhập, nút, tab |
| `text-caption` | 13px | 1.45 | 400 | Gợi ý, chữ phụ, chú thích |

Các utility mặc định `text-sm`, `text-lg`… vẫn còn. Ưu tiên bậc theo vai trò ở trên để các màn hình đồng nhất.

### Token màu

Token đặt tên theo vai trò, dùng như mọi màu Tailwind: `bg-primary`, `text-muted-foreground`, `border-input`, `outline-ring`. Bảng màu mặc định của Tailwind đã bị tắt (`--color-*: initial`), nên viết `bg-slate-200` sẽ không sinh CSS.

| Token | Giá trị | Nguồn | Dùng cho |
| --- | --- | --- | --- |
| `background` | `#ffffff` | | Nền trang |
| `surface` | `#f5f8fc` | | Nền khối, thẻ nổi nhẹ |
| `surface-muted` | `#eaf0f7` | | Nền khối phụ, skeleton |
| `foreground` | `#03172f` | Chữ "Examind" | Chữ chính |
| `muted-foreground` | `#4a5b73` | | Chữ phụ, gợi ý |
| `border` | `#d5dfeb` | | Đường chia, viền thẻ. Chỉ trang trí, không dùng làm viền ô nhập |
| `input` | `#7a8aa0` | | Viền ô nhập, checkbox |
| `primary` | `#0b3a7a` | Thân biểu tượng | Nút chính, link chính |
| `primary-hover` | `#082c5e` | | Hover của nút chính |
| `primary-foreground` | `#ffffff` | | Chữ trên nền `primary` và nền trạng thái đặc |
| `primary-subtle` | `#e8f0fa` | | Nền chọn, nền nút phụ khi hover |
| `accent` | `#00a0c8` | Ngôi sao, chấm chữ i | Nền nhấn, icon, minh hoạ. Chữ trên nền này dùng `foreground` |
| `accent-strong` | `#006b8a` | | Chữ hoặc link màu nhấn trên nền sáng |
| `accent-subtle` | `#e6f6fa` | | Nền nhấn nhạt, vùng chọn chữ |
| `ring` | `#0086ad` | | Vòng focus |
| `success` / `success-subtle` | `#15803d` / `#ecfdf3` | | Thành công |
| `warning` / `warning-subtle` | `#b45309` / `#fff7e6` | | Cảnh báo |
| `danger` / `danger-hover` / `danger-subtle` | `#b42318` / `#9a1d14` / `#fef1f0` | | Lỗi, xoá, viền ô nhập lỗi |
| `info` / `info-subtle` | `#0b63a8` / `#eaf3fc` | | Thông tin |

Quy ước màu trạng thái: `<tên>` dùng cho chữ, icon, viền và nền đặc có chữ `primary-foreground`. `<tên>-subtle` dùng làm nền `Alert` hoặc `Badge`, chữ trên đó dùng `<tên>`.

Màu cam ở chỏm mũ linh vật chỉ thuộc hình minh hoạ, không đưa vào token.

### Tương phản WCAG

Tính theo công thức độ sáng tương đối của WCAG 2.1 trên giá trị token trong `globals.css`.

| Chữ / thành phần | Nền | Tỉ lệ | Ngưỡng | Kết quả |
| --- | --- | --- | --- | --- |
| `foreground` | `background` | 17.99:1 | 4.5:1 | Đạt |
| `foreground` | `surface` | 16.89:1 | 4.5:1 | Đạt |
| `foreground` | `surface-muted` | 15.68:1 | 4.5:1 | Đạt |
| `muted-foreground` | `background` | 6.92:1 | 4.5:1 | Đạt |
| `muted-foreground` | `surface` | 6.50:1 | 4.5:1 | Đạt |
| `muted-foreground` | `surface-muted` | 6.03:1 | 4.5:1 | Đạt |
| `primary-foreground` | `primary` | 11.05:1 | 4.5:1 | Đạt |
| `primary-foreground` | `primary-hover` | 13.71:1 | 4.5:1 | Đạt |
| `primary` | `background` | 11.05:1 | 4.5:1 | Đạt |
| `primary` | `primary-subtle` | 9.62:1 | 4.5:1 | Đạt |
| `foreground` | `accent` | 5.88:1 | 4.5:1 | Đạt |
| `accent-strong` | `background` | 6.05:1 | 4.5:1 | Đạt |
| `accent-strong` | `accent-subtle` | 5.45:1 | 4.5:1 | Đạt |
| `input` (viền ô nhập) | `background` | 3.52:1 | 3:1 | Đạt |
| `input` (viền ô nhập) | `surface` | 3.30:1 | 3:1 | Đạt |
| `ring` (focus) | `background` | 4.19:1 | 3:1 | Đạt |
| `ring` (focus) | `surface` | 3.93:1 | 3:1 | Đạt |
| `accent` (icon) | `background` | 3.06:1 | 3:1 | Đạt |
| `success` | `background` | 5.02:1 | 4.5:1 | Đạt |
| `success` | `success-subtle` | 4.76:1 | 4.5:1 | Đạt |
| `primary-foreground` | `success` | 5.02:1 | 4.5:1 | Đạt |
| `warning` | `background` | 5.02:1 | 4.5:1 | Đạt |
| `warning` | `warning-subtle` | 4.71:1 | 4.5:1 | Đạt |
| `primary-foreground` | `warning` | 5.02:1 | 4.5:1 | Đạt |
| `danger` (chữ, viền lỗi) | `background` | 6.57:1 | 4.5:1 | Đạt |
| `danger` | `danger-subtle` | 5.97:1 | 4.5:1 | Đạt |
| `primary-foreground` | `danger` | 6.57:1 | 4.5:1 | Đạt |
| `primary-foreground` | `danger-hover` | 8.20:1 | 4.5:1 | Đạt |
| `info` | `background` | 6.24:1 | 4.5:1 | Đạt |
| `info` | `info-subtle` | 5.57:1 | 4.5:1 | Đạt |
| `primary-foreground` | `info` | 6.24:1 | 4.5:1 | Đạt |

Không dùng chữ màu `accent` (`#00a0c8`) trên nền trắng vì chỉ đạt 3.06:1. Dùng `accent-strong` thay thế.

## Luồng dữ liệu và tích hợp

`layout.tsx` gắn class biến font lên `<html>`. `globals.css` khai báo `--font-sans` trong `@theme inline` trỏ tới biến đó, nên `font-sans` và font mặc định của trang đều là Be Vietnam Pro. Token màu sinh ra utility Tailwind và biến CSS `--color-<tên>`, dùng được trong class hoặc trong CSS tự viết:

```tsx
<button className="rounded-md bg-primary px-4 py-2 text-label text-primary-foreground hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
  Tạo đề ôn
</button>

<p className="text-caption text-danger" id="email-error">Email chưa đúng định dạng.</p>
```

Khi thêm hoặc đổi token: sửa `globals.css`, tính lại tỉ lệ tương phản cho các cặp liên quan, cập nhật bảng ở trên. Nếu đổi `background` hoặc `foreground` thì sửa cả `manifest.ts`.

## Quyết định và cách kiểm chứng

- **Một font, Be Vietnam Pro**, lý do ở mục Font chữ.
- **Tắt bảng màu mặc định của Tailwind** để lỡ dùng `slate-*`, `cyan-*` thì không sinh CSS và dễ phát hiện khi review.
- **Chưa làm dark mode.** Không khai báo token tối để tránh bộ token dở dang. Khi làm, thêm giá trị tối cho cùng tên token, không tạo tên mới.
- **Motion cho hiệu ứng**: API khai báo hợp với React, hỗ trợ `AnimatePresence` cho phần tử rời khỏi DOM và tôn trọng giảm chuyển động bằng một cấu hình chung.
- **Header không còn ở root layout**: mỗi khu (landing, admin, auth sau này) tự đặt `Navbar` hoặc header riêng. `/admin` có `app/admin/layout.tsx` giữ logo như trước.
- **Chưa làm**: 4 trang auth (đăng nhập, đăng ký, quên mật khẩu, đặt lại mật khẩu), thuộc bước tiếp theo của issue #16.

Lệnh đã chạy trong `frontend/` ngày 2026-11-28:

```bash
npm ci
npm run typecheck
npm run build   # build qua, route /, /admin, /design-system, /manifest.webmanifest prerender tĩnh
```

Đã xem bằng `npm run dev` ở 1280px và 360px: splash tắt sau khi chạy hết các bước, landing không cuộn ngang ở 360px, menu mobile mở và đóng được, nút Đăng nhập hiện toast mà không đổi URL, `/design-system` hiển thị đủ 6 nhóm, console không có lỗi. Chưa kiểm ở 768px và chưa thử với trình đọc màn hình thật.

Kiểm không còn màu ngoài token (chạy ở thư mục gốc repo, kết quả mong đợi chỉ còn các dòng trong `manifest.ts` và `viewport` của `layout.tsx`):

```bash
grep -rnE "(slate|cyan|gray|zinc|sky|blue|red|green|amber|white|black)-[0-9]{2,3}" frontend/src
grep -rnE "#[0-9a-fA-F]{6}|rgb\(" frontend/src | grep -v globals.css
```

## Tài liệu liên quan

- [Kiến trúc frontend](frontend-base.md)
- [Đặc tả sản phẩm](../../spec.md)
- [Issue #16](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/16)
- [WCAG 2.1 — Contrast (Minimum)](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [Tailwind CSS — Theme variables](https://tailwindcss.com/docs/theme)
