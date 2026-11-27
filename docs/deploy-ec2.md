# Truy cập VPS AWS EC2 · Examind

## Thông tin kết nối

| Thông tin | Giá trị |
| --- | --- |
| Instance | Examind (`i-0931f2a3b4010b6b3`) |
| Vùng AWS | Sydney (`ap-southeast-2`) |
| Loại instance | `t8i.small` |
| Hệ điều hành | Ubuntu 26.04.1 LTS |
| IPv4 công khai | `32.236.15.241` |
| DNS công khai | `ec2-32-236-15-241.ap-southeast-2.compute.amazonaws.com` |
| SSH | `ubuntu`, cổng `22` |

Địa chỉ trên đã được kiểm tra ngày 27/11/2026. IPv4 công khai được cấp tự động và có thể đổi khi dừng rồi khởi động lại instance. Lấy địa chỉ mới trong **EC2 → Instances → Examind** nếu cần. [Tài liệu AWS về dừng và khởi động EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Stop_Start.html)

## Địa chỉ API cho frontend

DNS công khai của EC2 trỏ tới `32.236.15.241`. Sau khi backend được triển khai và cổng HTTP(S) được phép truy cập, frontend có thể dùng DNS này làm `baseURL`. Ví dụ, nếu FastAPI được phục vụ trực tiếp trên cổng `8000`, hãy thử `http://ec2-32-236-15-241.ap-southeast-2.compute.amazonaws.com:8000/api/v1/health` từ máy ngoài EC2.

Hiện instance chỉ đang lắng nghe SSH trên cổng `22` ở giao diện công khai, nên URL ví dụ chưa phục vụ API. Nếu frontend chạy HTTPS, dùng URL API HTTPS có chứng chỉ hợp lệ. Khi trình duyệt gọi từ origin khác, cấu hình CORS của FastAPI cho origin frontend.

## Kết nối từ máy cá nhân

Dùng OpenSSH và tệp `.pem` được cấp riêng cho instance. Nếu tệp `backend-key.pem` nằm ở thư mục gốc repo, chạy lệnh sau. Thay đường dẫn sau `-i` nếu bạn lưu khóa ở nơi khác.

```powershell
ssh -o IdentitiesOnly=yes -i .\backend-key.pem -p 22 ubuntu@32.236.15.241
```

Trên macOS hoặc Linux, dùng `./backend-key.pem`. Nếu OpenSSH báo quyền đọc quá rộng, chạy `chmod 600 ./backend-key.pem` rồi kết nối lại.

Ở lần đầu kết nối, đối chiếu fingerprint mà OpenSSH hiển thị với fingerprint lấy qua AWS Console trước khi chấp nhận. Để kết nối từ máy mới, Security Group cần cho phép TCP 22 từ địa chỉ IP nguồn của máy đó. [Hướng dẫn SSH của AWS](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-linux-inst-ssh.html)

Git đã bỏ qua các tệp `.pem` theo quy tắc `*.pem` trong `.gitignore`. Nhận khóa qua kênh được nhóm cấp riêng và giữ khóa ngoài các tệp commit.

## Kiểm tra sau khi đăng nhập

```bash
whoami
hostname
cat /var/lib/cloud/data/instance-id
grep ^PRETTY_NAME= /etc/os-release
```

Kết quả đã xác nhận qua SSH là user `ubuntu`, hostname `ip-172-31-20-96` và instance ID `i-0931f2a3b4010b6b3`. Tại thời điểm kiểm tra, lệnh `docker` chưa có trong `PATH` của user `ubuntu`. Khi môi trường triển khai đã được thiết lập, chạy `docker compose ps` trong thư mục có tệp Compose trên máy chủ để xem trạng thái dịch vụ.

## Xử lý lỗi

- **`UNPROTECTED PRIVATE KEY FILE` trên Windows.** Mở **Properties → Security → Advanced** của đúng tệp `.pem`. Tắt kế thừa và giữ quyền truy cập cho tài khoản Windows đang dùng để chạy SSH. Sau đó thử lại.
- **`Permission denied (publickey)`.** Kiểm tra username là `ubuntu`, đường dẫn sau `-i` và tệp `.pem` có đúng với key pair của instance.
- **`Connection timed out`.** Kiểm tra IPv4/DNS hiện tại, trạng thái instance và inbound TCP 22 từ IP nguồn trong Security Group. [Hướng dẫn xử lý lỗi SSH của AWS](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/TroubleshootingInstancesConnecting.html)
