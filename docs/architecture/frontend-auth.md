# Trang xác thực frontend

Dành cho người phát triển frontend cần sửa hoặc nối API cho các trang đăng nhập, đăng ký, quên mật khẩu, nhập mã OTP và đặt mật khẩu mới, và cho lớp chặn route theo vai trò. Mọi luồng đều dùng được API thật. Mock chỉ bật khi đặt `NEXT_PUBLIC_MOCK_MODE=true` hoặc chạy dev mà không đặt biến này.

## Bối cảnh và ràng buộc

Issue #16 yêu cầu các trang auth đủ trạng thái: đang gửi, thành công, sai thông tin, lỗi từng trường, tài khoản bị khoá, phiên hết hạn và lỗi mạng. Nhãn phải gắn với ô nhập, focus chuyển tới trường sai đầu tiên, `autocomplete` đúng loại, và chỉ gọi API qua lớp API chung của feature.

Backend auth có từ PR #26. Issue #25 bổ sung xác minh đăng ký và Google Sign-In theo [hợp đồng API](../api/auth-api.md).

## Thành phần và trách nhiệm

| Vị trí trong `frontend/src/` | Trách nhiệm |
| --- | --- |
| `app/(auth)/layout.tsx` | Khung hai cột. Cột trái là `AuthAside` (linh vật và lời giới thiệu theo route, ẩn trên màn hình nhỏ), cột phải là logo và form. Không có nút về trang chủ vì khách không có trang chủ |
| `app/(auth)/template.tsx` | Hiệu ứng trượt vào mỗi khi đổi trang auth |
| `app/(auth)/login/page.tsx` | `/login`. Đọc `?reason=session-expired \| password-reset \| logged-out`, giá trị khác bị bỏ qua |
| `app/(auth)/register`, `forgot-password`, `verify-otp`, `reset-password` | Mỗi trang chỉ render form tương ứng |
| `features/auth/api.ts` | `authApi`: gọi API theo cùng origin. Bật mock bằng `NEXT_PUBLIC_MOCK_MODE=true`. Lỗi 422 đổi thành lỗi từng trường |
| `features/auth/mock.ts` | API giả lập, lưu trạng thái ở `sessionStorage` key `examind:mock-auth` |
| `features/auth/types.ts` | `User`, `AuthErrorCode`, lớp `AuthError` và `toAuthError` |
| `features/auth/validation.ts` | Kiểm tra email, mật khẩu mới (8–128 ký tự), xác nhận mật khẩu, tên hiển thị, độ mạnh mật khẩu, che email |
| `features/auth/use-auth-form.ts` | Hook form: giá trị, lỗi, trạng thái gửi, gộp lỗi từ server, focus trường sai đầu tiên |
| `features/auth/route-guard.tsx` | `AuthGuard` bọc mọi trang trong `AppProvider`, chặn route theo phiên và vai trò (xem mục bên dưới) |
| `lib/api-client.ts` | `onSessionLost`: API nào trả `SESSION_*` hoặc `ACCOUNT_DISABLED` (trừ `/auth/me`, `/auth/login`, `/auth/logout`) thì provider dispatch `signedOut('session-expired')` |
| `features/auth/auth-slice.ts` | Reducer `auth`: `{ user, status: 'unknown' \| 'authenticated' \| 'guest' }`. `reason` (`session-expired` hoặc `logged-out`) cho trang đăng nhập hiện thông báo. Chỉ lưu `UserOut`, không lưu token |
| `features/auth/reset-flow.ts` | Lưu email và `reset_token` của luồng quên mật khẩu trong `sessionStorage` key `examind:reset-flow`, để email không nằm trên URL |
| `features/auth/forms/` | Năm form: đăng nhập, đăng ký, quên mật khẩu, nhập OTP, đặt mật khẩu mới |
| `features/auth/components/` | `AuthAside`, `AuthHeader`, `PasswordStrength`, `UserMenu` (tên người dùng và nút đăng xuất, dùng ở navbar học sinh và header admin) |
| `components/ui/otp-input.tsx` | Ô OTP 6 số: tự chuyển ô, dán cả mã, Backspace, phím mũi tên, `autocomplete="one-time-code"`, rung khi sai |
| `lib/use-hydrated.ts` | Trả `false` khi hydrate, để UI phụ thuộc user trong store khớp HTML từ server |

Splash khởi động gọi `authApi.me()` rồi dispatch `signedIn` hoặc `signedOut`. Trong lúc chưa biết phiên, `AuthGuard` hiện spinner thay cho trang cần đăng nhập.

### Chặn route theo vai trò

Web chỉ có hai loại người dùng: học sinh và admin. Không có trang cho khách.

| Người dùng | Được vào | Mở trang khác thì chuyển tới |
| --- | --- | --- |
| Chưa đăng nhập | `/login`, `/register`, `/forgot-password`, `/verify-otp`, `/reset-password`, `/login/google` | `/login` (kèm `?reason=` nếu vừa đăng xuất hoặc hết phiên) |
| Học sinh | `/` và các trang ngoài `/admin`, cùng `/design-system` | `/` |
| Admin | `/admin/*`, `/design-system` | `/admin` |

Đã đăng nhập mà mở trang auth thì về trang chủ theo vai trò. Đăng xuất dispatch `signedOut('logged-out')`, guard đưa về `/login?reason=logged-out`. Guard chỉ là lớp giao diện, quyền thật do backend kiểm ở từng API. Trang `/` hiện vẫn là nội dung landing (đã bỏ các nút đăng ký) cho tới khi có khu học tập của #4.

## Luồng dữ liệu và tích hợp

### Đăng nhập và đăng ký

1. Form kiểm tra phía client. Có lỗi thì hiện lỗi dưới từng ô và focus ô sai đầu tiên.
2. Đăng ký gọi `authApi.register` rồi mở bước OTP. Đăng nhập bằng mật khẩu đúng mở phiên ngay.
3. Khi dùng API thật, cả hai trang có nút Google. Trang `/login/google` dùng verifier của tab để đổi ticket thành phiên. Nếu backend yêu cầu OTP cho email ngoài Google, trang hiển thị bước xác minh.
4. Sau khi có phiên, dispatch `signedIn`. Admin chuyển tới `/admin`, học sinh chuyển tới `/`.
5. Lỗi được đổi thành `AuthError` và hiện bằng `Alert`: sai thông tin (`INVALID_CREDENTIALS`), tài khoản bị khoá (`ACCOUNT_DISABLED`), email đã dùng (`EMAIL_TAKEN`, kèm lỗi ở ô email), lỗi mạng (`NETWORK`, có nút "Thử lại").

### Quên mật khẩu

```
/forgot-password ──email──▶ /verify-otp ──mã 6 số──▶ /reset-password ──mật khẩu mới──▶ /login?reason=password-reset
```

- Trang quên mật khẩu luôn báo "đã gửi mã" kể cả khi email chưa đăng ký, để không lộ email nào có tài khoản.
- Trang OTP hiện email đã che, cho gửi lại mã sau 60 giây, báo số lần thử còn lại, mã hết hạn và bị khoá do nhập sai nhiều lần.
- Trang đặt mật khẩu mới cần `reset_token` trong `examind:reset-flow`. Không có thì báo phiên hết hiệu lực và cho bắt đầu lại.

### Hợp đồng API quên mật khẩu

Backend đã có, xem [API xác thực](../api/auth-api.md#quên-mật-khẩu). Backend không trả số lần thử còn lại, nên ở API thật trang OTP chỉ báo "mã chưa đúng". Gửi lại quá sớm (429 `OTP_RESEND_LIMIT`) hoặc lỗi gửi thư (503) hiện thông báo từ máy chủ thay cho lỗi mạng.

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
