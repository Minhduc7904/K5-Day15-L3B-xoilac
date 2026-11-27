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
| IPv4 công khai (Elastic IP) | `54.79.136.46` |
| Tên miền | `examind.duckdns.org` (DuckDNS, trỏ về Elastic IP) |
| DNS công khai của AWS | `ec2-54-79-136-46.ap-southeast-2.compute.amazonaws.com` |
| SSH | `ubuntu`, cổng `22` |

Ngày 27/11/2026 instance được gắn **Elastic IP** `54.79.136.46` (thay cho IP cấp tự động `32.236.15.241`), nên IP không đổi khi dừng rồi khởi động lại. AWS tính phí mọi IPv4 công khai (kể cả Elastic IP đang gắn vào instance; tài khoản free tier được miễn 750 giờ/tháng trong 12 tháng đầu), nên khi không dùng nữa hãy giải phóng (Release) trong **EC2 → Elastic IPs** để khỏi bị tính phí. Tên miền `examind.duckdns.org` cấu hình trên [duckdns.org](https://www.duckdns.org). Nếu Elastic IP đổi, cập nhật ô current ip ở DuckDNS và các secret `EC2_HOST`, `EC2_KNOWN_HOSTS` (xem [deploy-backend-ci-cd.md](deploy-backend-ci-cd.md)).

## Các bước thực hiện

1. **Kết nối SSH.** Từ thư mục gốc repo, chạy lệnh sau hoặc thay đường dẫn sau `-i` bằng vị trí tệp của bạn.

   ```powershell
   ssh -o IdentitiesOnly=yes -i .\backend-key.pem -p 22 ubuntu@54.79.136.46
   ```

   Trên macOS hoặc Linux, dùng đường dẫn `./backend-key.pem`.

2. **Tra địa chỉ API cho frontend.** Backend được phục vụ qua nginx ở cổng 80 và **443** (cổng 8000 chỉ nghe nội bộ trên VPS, không mở ra ngoài). Frontend trên Vercel (HTTPS) phải dùng địa chỉ HTTPS, nếu không trình duyệt chặn vì mixed content.

   ```text
   API:    https://examind.duckdns.org/api/v1
   Socket: wss://examind.duckdns.org   (đường dẫn /api/socket.io, issue #36)
   ```

   Chứng chỉ Let's Encrypt do `deploy/remote-deploy.sh` xin ở lần deploy đầu và container `certbot` tự gia hạn. Cần cả cổng **80** (xác minh tên miền) và **443** mở trong Security Group. Cổng 80 vẫn phục vụ API qua HTTP để kiểm sức khoẻ. Frontend gọi từ origin khác thì cho phép origin đó trong `CORS_ORIGINS` của `/opt/examind/prod.env` trên VPS (nhiều origin phân tách bằng dấu phẩy).

## Kiểm tra kết quả

Sau khi SSH thành công, chạy trên EC2.

```bash
whoami
hostname
cat /var/lib/cloud/data/instance-id
grep ^PRETTY_NAME= /etc/os-release
```

Kết quả đã xác nhận là user `ubuntu`, hostname `ip-172-31-20-96` và instance ID `i-0931f2a3b4010b6b3`. Lần kiểm tra ngày 27/11/2026 chỉ thấy SSH lắng nghe trên giao diện công khai và chưa tìm thấy lệnh `docker` trong `PATH` của user `ubuntu`.

Từ ngày 27/11/2026, VPS đã cài Docker và chạy backend qua nginx; quy trình tự động nằm ở [Deploy backend CI/CD](deploy-backend-ci-cd.md). Sau khi môi trường triển khai đã sẵn sàng, chạy `docker compose ps` từ thư mục có tệp Compose trên máy chủ và gọi `http://examind.duckdns.org/api/v1/health` từ máy ngoài EC2 để xác nhận API phản hồi.

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
