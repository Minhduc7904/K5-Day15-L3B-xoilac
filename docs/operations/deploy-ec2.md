# Truy cập VPS AWS EC2 · Examind

Dùng runbook này để đăng nhập VPS demo qua SSH và kiểm tra địa chỉ API dành cho frontend.

## Điều kiện trước khi chạy

- Máy cá nhân có OpenSSH và tệp `.pem` được cấp cho instance.
- Security Group cho phép TCP 22 từ IP nguồn của máy cá nhân. Khi kết nối lần đầu, đối chiếu fingerprint với thông tin lấy qua AWS Console trước khi chấp nhận.
- Các lệnh PowerShell bên dưới chạy từ thư mục gốc repo nếu khóa được lưu tại `backend-key.pem`. Git bỏ qua các tệp `.pem` theo quy tắc có sẵn trong `.gitignore`. Nhận khóa qua kênh riêng của nhóm.

## Thông tin môi trường

| Thông tin | Giá trị |
| --- | --- |
| Instance | Examind (`i-0931f2a3b4010b6b3`) |
| Vùng AWS | Sydney (`ap-southeast-2`) |
| Loại instance | `t8i.small` |
| Hệ điều hành | Ubuntu 26.04.1 LTS |
| IPv4 công khai | `32.236.15.241` |
| DNS công khai | `ec2-32-236-15-241.ap-southeast-2.compute.amazonaws.com` |
| SSH | `ubuntu`, cổng `22` |

Đã kiểm tra kết nối và DNS ngày 27/11/2026. IPv4 công khai được cấp tự động và có thể đổi sau khi dừng rồi khởi động lại instance. Lấy địa chỉ mới trong **AWS Console → EC2 → Instances → Examind** khi cần.

## Các bước thực hiện

1. **Kết nối SSH.** Từ thư mục gốc repo, chạy lệnh sau hoặc thay đường dẫn sau `-i` bằng vị trí tệp của bạn.

   ```powershell
   ssh -o IdentitiesOnly=yes -i .\backend-key.pem -p 22 ubuntu@32.236.15.241
   ```

   Trên macOS hoặc Linux, dùng đường dẫn `./backend-key.pem`.

2. **Tra địa chỉ API cho frontend sau khi deploy.** DNS công khai dùng được làm host của `baseURL` khi FastAPI đang phục vụ và Security Group cho phép cổng tương ứng. Ví dụ dưới đây giả sử backend phục vụ HTTP trực tiếp trên cổng `8000`.

   ```text
   http://ec2-32-236-15-241.ap-southeast-2.compute.amazonaws.com:8000
   ```

   Với frontend dùng HTTPS, cấu hình URL API HTTPS có chứng chỉ hợp lệ. Nếu frontend gọi từ origin khác, cho phép origin đó trong cấu hình CORS của FastAPI.

## Kiểm tra kết quả

Sau khi SSH thành công, chạy trên EC2.

```bash
whoami
hostname
cat /var/lib/cloud/data/instance-id
grep ^PRETTY_NAME= /etc/os-release
```

Kết quả đã xác nhận là user `ubuntu`, hostname `ip-172-31-20-96` và instance ID `i-0931f2a3b4010b6b3`. Lần kiểm tra ngày 27/11/2026 chỉ thấy SSH lắng nghe trên giao diện công khai và chưa tìm thấy lệnh `docker` trong `PATH` của user `ubuntu`.

Sau khi môi trường triển khai đã sẵn sàng, chạy `docker compose ps` từ thư mục có tệp Compose trên máy chủ và gọi `<baseURL>/api/v1/health` từ máy ngoài EC2 để xác nhận API phản hồi.

## Xử lý lỗi

| Triệu chứng | Kiểm tra |
| --- | --- |
| `UNPROTECTED PRIVATE KEY FILE` | Trên Windows, mở **Properties → Security → Advanced** của đúng tệp `.pem`, tắt kế thừa và giữ quyền truy cập cho tài khoản đang chạy SSH. Trên macOS hoặc Linux, dùng `chmod 600 ./backend-key.pem`. |
| `Permission denied (publickey)` | Kiểm tra username `ubuntu`, đường dẫn khóa và key pair của instance. |
| `Connection timed out` | Kiểm tra địa chỉ hiện tại, trạng thái instance và inbound TCP 22 từ IP nguồn. |
| SSH được nhưng API lỗi | Kiểm tra dịch vụ đang chạy, cổng và giao thức trong `baseURL`, Security Group và cấu hình CORS nếu chỉ lỗi trong trình duyệt. |

## Tài liệu liên quan

- [Mục lục tài liệu Examind](../README.md)
- [Kết nối EC2 bằng SSH](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-linux-inst-ssh.html)
- [Xử lý lỗi kết nối EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/TroubleshootingInstancesConnecting.html)
- [Dừng và khởi động lại EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Stop_Start.html)
