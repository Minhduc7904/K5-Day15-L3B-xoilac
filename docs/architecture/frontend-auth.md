# Trang xác thực frontend

Dành cho người phát triển frontend cần sửa hoặc nối API cho các trang đăng nhập, đăng ký, quên mật khẩu, nhập mã OTP và đặt mật khẩu mới. Hiện mọi trang chạy bằng **mock**, chưa gọi backend thật.

## Bối cảnh và ràng buộc

Issue #16 yêu cầu các trang auth đủ trạng thái: đang gửi, thành công, sai thông tin, lỗi từng trường, tài khoản bị khoá, phiên hết hạn và lỗi mạng. Nhãn phải gắn với ô nhập, focus chuyển tới trường sai đầu tiên, `autocomplete` đúng loại, và chỉ gọi API qua lớp API chung của feature.

Frontend bám hợp đồng `register`, `login`, `logout` và `me` của backend auth ở [PR #17](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/pull/17). PR này đã bị revert ở [PR #18](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/pull/18), nên hiện **backend chưa có endpoint auth nào** và frontend chạy hoàn toàn bằng mock. Luồng quên mật khẩu bằng OTP cũng chưa có, frontend dùng hợp đồng đề xuất ở mục dưới. Khi backend auth quay lại, đối chiếu lại `features/auth/api.ts` với hợp đồng mới.

## Thành phần và trách nhiệm

| Vị trí trong `frontend/src/` | Trách nhiệm |
| --- | --- |
| `app/(auth)/layout.tsx` | Khung hai cột. Cột trái là `AuthAside` (linh vật và lời giới thiệu theo route, ẩn trên màn hình nhỏ), cột phải là logo, nút "Trang chủ" và form |
| `app/(auth)/template.tsx` | Hiệu ứng trượt vào mỗi khi đổi trang auth |
| `app/(auth)/login/page.tsx` | `/login`. Đọc `?reason=session-expired \| password-reset \| logged-out`, giá trị khác bị bỏ qua |
| `app/(auth)/register`, `forgot-password`, `verify-otp`, `reset-password` | Mỗi trang chỉ render form tương ứng |
| `features/auth/api.ts` | `authApi`: mock khi `NEXT_PUBLIC_MOCK_MODE` khác `false`, ngược lại gọi Axios với `withCredentials`. Lỗi 422 đổi thành lỗi từng trường |
| `features/auth/mock.ts` | API giả lập, lưu trạng thái ở `sessionStorage` key `examind:mock-auth` |
| `features/auth/types.ts` | `User`, `AuthErrorCode`, lớp `AuthError` và `toAuthError` |
| `features/auth/validation.ts` | Kiểm tra email, mật khẩu (6–128 ký tự), xác nhận mật khẩu, tên hiển thị, độ mạnh mật khẩu, che email |
| `features/auth/use-auth-form.ts` | Hook form: giá trị, lỗi, trạng thái gửi, gộp lỗi từ server, focus trường sai đầu tiên |
| `features/auth/auth-slice.ts` | Reducer `auth`: `{ user, status: 'unknown' \| 'authenticated' \| 'guest' }`. Chỉ lưu `UserOut`, không lưu token |
| `features/auth/reset-flow.ts` | Lưu email và `reset_token` của luồng quên mật khẩu trong `sessionStorage` key `examind:reset-flow`, để email không nằm trên URL |
| `features/auth/forms/` | Năm form: đăng nhập, đăng ký, quên mật khẩu, nhập OTP, đặt mật khẩu mới |
| `features/auth/components/` | `AuthAside`, `AuthHeader`, `PasswordStrength`, `SignedInNotice` (báo khi đã đăng nhập mà vẫn mở trang auth) |
| `components/ui/otp-input.tsx` | Ô OTP 6 số: tự chuyển ô, dán cả mã, Backspace, phím mũi tên, `autocomplete="one-time-code"`, rung khi sai |
| `lib/use-hydrated.ts` | Trả `false` khi hydrate, để UI phụ thuộc user trong store khớp HTML từ server |

Splash khởi động gọi `authApi.me()` rồi dispatch `signedIn` hoặc `signedOut`. Navbar landing (`features/landing/auth-actions.tsx`) hiện skeleton cho tới khi biết trạng thái.

## Luồng dữ liệu và tích hợp

### Đăng nhập và đăng ký

1. Form kiểm tra phía client. Có lỗi thì hiện lỗi dưới từng ô và focus ô sai đầu tiên.
2. Gọi `authApi.login` hoặc `authApi.register`. Nút chuyển sang trạng thái đang gửi.
3. Thành công thì dispatch `signedIn`. Admin chuyển tới `/admin`, học sinh chuyển tới `/`.
4. Lỗi được đổi thành `AuthError` và hiện bằng `Alert`: sai thông tin (`INVALID_CREDENTIALS`), tài khoản bị khoá (`ACCOUNT_DISABLED`), email đã dùng (`EMAIL_TAKEN`, kèm lỗi ở ô email), lỗi mạng (`NETWORK`, có nút "Thử lại").

### Quên mật khẩu

```
/forgot-password ──email──▶ /verify-otp ──mã 6 số──▶ /reset-password ──mật khẩu mới──▶ /login?reason=password-reset
```

- Trang quên mật khẩu luôn báo "đã gửi mã" kể cả khi email chưa đăng ký, để không lộ email nào có tài khoản.
- Trang OTP hiện email đã che, cho gửi lại mã sau 60 giây, báo số lần thử còn lại, mã hết hạn và bị khoá do nhập sai nhiều lần.
- Trang đặt mật khẩu mới cần `reset_token` trong `examind:reset-flow`. Không có thì báo phiên hết hiệu lực và cho bắt đầu lại.

### Hợp đồng API đề xuất cho quên mật khẩu

**Chưa có ở backend.** Frontend gọi đúng các đường dẫn này ở `api.ts`. Backend có thể đổi, khi đó sửa `api.ts` và mục này cùng lúc.

| Request | Body | Thành công | Lỗi |
| --- | --- | --- | --- |
| `POST /auth/password/forgot` | `{ "email" }` | 204, kể cả khi email không tồn tại | 422 email sai định dạng |
| `POST /auth/password/verify-otp` | `{ "email", "otp" }` | 200 `{ "reset_token" }` | 400 `OTP_INVALID` kèm số lần còn lại, 400 `OTP_EXPIRED`, 429 `TOO_MANY_ATTEMPTS` |
| `POST /auth/password/reset` | `{ "reset_token", "password" }` | 204 | 400 `RESET_TOKEN_INVALID`, 422 mật khẩu không hợp lệ |

### Mock

Mỗi lời gọi mock chờ khoảng 0,25–0,9 giây để thấy trạng thái đang gửi. Tài khoản chỉ dùng cho mock, email thuộc tên miền tài liệu `example.com`, mật khẩu là giá trị mẫu.

| Email | Mật khẩu mẫu | Kết quả |
| --- | --- | --- |
| `hs01@example.com` | `hs01-demo` | Học sinh, đăng nhập thành công |
| `admin@example.com` | `admin-demo-123` | Quản trị, chuyển tới `/admin` |
| `khoa@example.com` | `khoa-demo` | `ACCOUNT_DISABLED` |
| `loimang@example.com` | bất kỳ | Giả lập lỗi mạng ở mọi thao tác nhận email |

| Mã OTP | Kết quả |
| --- | --- |
| `123456` | Đúng, cấp `reset_token` |
| `000000` | `OTP_EXPIRED` |
| Mã khác | `OTP_INVALID`. Sai 5 lần thì `TOO_MANY_ATTEMPTS` |

Trong mock, mã hết hạn sau 5 phút. Toast trên trang quên mật khẩu hiện sẵn mã để dễ thử. Đăng ký tài khoản mới bằng mock thì đăng nhập lại được trong cùng tab. Trên trang đăng nhập có ô "Tài khoản thử" để điền nhanh, chỉ hiện ở chế độ mock.

## Quyết định và cách kiểm chứng

- Mock nằm sau cùng interface `authApi` nên nối API thật chỉ cần đặt `NEXT_PUBLIC_MOCK_MODE=false`, không sửa form.
- Store chỉ giữ `UserOut`. Phiên do cookie `HttpOnly` của backend giữ.
- Email của luồng quên mật khẩu lưu ở `sessionStorage` thay vì query string, để không lộ trong lịch sử trình duyệt và log.
- UI phụ thuộc user chỉ render sau khi hydrate (`useHydrated`). Splash nạp user trước khi các route segment hydrate xong, nên render ngay sẽ lệch HTML từ server.

Đã kiểm ngày 2026-11-28 trong trình duyệt (dev, mock), màn hình 1280px:

- Đăng nhập: gửi form trống (lỗi và focus email), tài khoản bị khoá, lỗi mạng, sai mật khẩu, học sinh và admin thành công. Tải lại vẫn giữ phiên. Đăng xuất hoạt động.
- Đăng ký: lỗi từng trường, `EMAIL_TAKEN`, thành công.
- Quên mật khẩu chỉ bằng bàn phím: mã sai (báo số lần còn), mã hết hạn, gửi lại, mã đúng, đặt mật khẩu mới, đăng nhập bằng mật khẩu mới.
- Ở 360px và 768px không có thanh cuộn ngang trên mọi trang auth.
- Tải lại `/`, `/login`, `/register` khi đã đăng nhập không còn lỗi hydration trong console.

Lệnh: `npm run typecheck` và `npm run build` trong `frontend/` đều qua.

## Tài liệu liên quan

- [PR #17: backend auth (đã revert)](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/pull/17)
- [Kiến trúc frontend](frontend-base.md)
- [Design system frontend](frontend-design-system.md)
- [Issue #16](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/16)
