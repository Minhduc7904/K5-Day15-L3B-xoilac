# Tài liệu Examind

| Cần làm | Đọc |
| --- | --- |
| Chạy bản thử và hiểu cấu trúc repo | [README dự án](../README.md) |
| Nắm phạm vi, luồng AI và tiêu chí nghiệm thu | [Đặc tả dự án](../spec.md) |
| Hiểu các thành phần và luồng dữ liệu của hệ thống | [Tổng quan hệ thống](architecture/system-overview.md) |
| Viết tính năng mới trong backend | [Các lớp backend](architecture/backend-layers.md) |
| Hiểu đăng nhập, phiên và phân quyền; kiểm quyền cho endpoint mới | [Xác thực và phân quyền backend](architecture/backend-auth.md) |
| Gọi hoặc mock API đăng ký, đăng nhập, đăng xuất | [API xác thực](api/auth-api.md) |
| Viết tính năng mới trong frontend | [Kiến trúc frontend](architecture/frontend-base.md) |
| Dùng font, thang chữ và token màu chung của giao diện | [Design system frontend](architecture/frontend-design-system.md) |
| Sửa trang đăng nhập, đăng ký, quên mật khẩu, OTP hoặc dùng mock auth | [Trang xác thực frontend](architecture/frontend-auth.md) |
| Chạy frontend và deploy Vercel | [Runbook frontend](operations/deploy-frontend-vercel.md) |
| Chạy PostgreSQL, MinIO và backend trên máy | [Chạy bộ khung local](operations/run-local-stack.md) |
| Xem định dạng API và gọi thử endpoint mẫu | [API mẫu](api/sample-api.md) |
| Kết nối EC2 và kiểm tra khả năng truy cập API | [Runbook EC2](operations/deploy-ec2.md) |
| Deploy backend bằng GitHub Actions, sửa nginx | [Deploy backend CI/CD](operations/deploy-backend-ci-cd.md) |
| Dựng và nạp dữ liệu nền (câu hỏi, đề, ảnh) | [Nạp dữ liệu nền](operations/seed-base-data.md) |
| Cấu hình nhà cung cấp model cho bản thử | [Kết nối model](connect-model.md) |
| Ghi nhận cách nhóm dùng AI | [Nhật ký sử dụng AI](ai-usage.md) |
| Hiểu dữ liệu và đánh giá | [Data card](../data/DATA_CARD.md) · [Hướng dẫn eval](../eval/README.md) |

## Chọn vị trí và mẫu

| Loại tài liệu | Đường dẫn cho file mới | Mẫu |
| --- | --- | --- |
| Kiến trúc, trách nhiệm các lớp, luồng dữ liệu | `docs/architecture/<chủ-đề>.md` | [Kiến trúc](templates/architecture.md) |
| API HTTP, SSE và hợp đồng tích hợp | `docs/api/<tính-năng>-api.md` | [API](templates/api.md) |
| Chạy local, triển khai, vận hành và xử lý sự cố | `docs/operations/<thao-tác>-<đối-tượng>.md` | [Runbook](templates/runbook.md) |

Dùng tên tiếng Anh viết thường, chữ số nếu cần, phân tách bằng dấu gạch ngang và đuôi `.md`. Đặt tên theo chủ đề hoặc thao tác, ví dụ `backend-layers.md`, `exam-import-api.md`, `deploy-ec2.md`. `README.md` dùng cho trang mục lục. Các file nộp bài và đường dẫn mà bộ chạy đang dùng giữ đúng tên hiện hành.

Một tài liệu có một mục đích và một vị trí chính. Cập nhật tài liệu đang có trước khi tạo file mới. Khi di chuyển file, cập nhật mọi link trong repo. Giữ trang chỉ đường ở URL cũ nếu nhóm đã chia sẻ URL đó.

## Viết và rà soát

1. Mở mẫu theo loại tài liệu và giữ các mục áp dụng. Xóa phần hướng dẫn và placeholder. Nếu một mục bắt buộc chưa có dữ kiện, ghi rõ tình trạng và cách kiểm.
2. Dùng một tiêu đề cấp 1, rồi dùng các cấp tiêu đề theo thứ tự. Viết phần mở đầu theo việc người đọc cần làm. Dùng bước đánh số cho thao tác có thứ tự, bảng cho giá trị cần tra và code fence có ngôn ngữ cho lệnh hoặc dữ liệu mẫu.
3. Ghi môi trường, thư mục chạy lệnh và kết quả mong đợi khi chúng ảnh hưởng đến cách làm. Phân biệt bước đã kiểm chứng, ví dụ và phần dự kiến. Ghi ngày xác nhận cho dữ liệu có thể đổi.
4. Dùng liên kết tương đối trong repo và ưu tiên nguồn chính thức cho tài liệu bên ngoài. Dùng giá trị mẫu cho bí mật, khóa, dữ liệu học sinh và thông tin xác thực.
5. Cập nhật mục lục này khi thêm tài liệu chính. Trước khi bàn giao, kiểm link, lệnh mẫu và sự nhất quán với code hoặc API. Ghi rõ phần chưa kiểm được.

## Khi nào tài liệu là một phần của thay đổi

- Đổi hành vi hoặc điều kiện tích hợp API thì cập nhật tài liệu API và ví dụ lỗi tương ứng.
- Đổi ranh giới lớp, lưu trữ hoặc luồng dữ liệu thì cập nhật tài liệu kiến trúc liên quan.
- Đổi biến cấu hình, lệnh chạy, môi trường, deploy hoặc cách kiểm tra thì cập nhật runbook liên quan.
- Đổi dữ liệu hoặc cách đánh giá thì cập nhật tài liệu ngay cạnh dữ liệu hoặc bộ eval theo quy định trong [AGENTS.md](../AGENTS.md).

Danh sách phải đọc trước khi sửa nằm trong [AGENTS.md](../AGENTS.md#đọc-trước-khi-làm).
