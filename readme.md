# Video Streaming using IP Multicast (Socket Programming Project)

Dự án triển khai ứng dụng truyền tải video luồng (Video Streaming) thời gian thực sử dụng giao thức **IP Multicast** qua tầng vận chuyển **UDP**. Hệ thống cho phép một máy chủ (Server) phát tán các khung hình video liên tục tới một nhóm địa chỉ Multicast duy nhất và nhiều máy khách (Client) có thể đồng thời gia nhập nhóm để giải mã và hiển thị luồng video đó theo thời gian thực mà không làm tăng băng thông tải của Server.

---

## 👥 Thành viên thực hiện dự án

| STT | Họ và Tên | Mã số Sinh viên (MSSV) |
|---|---|---|
| 1 | **Ngô Bá Sỹ Nguyên** | 23120020 |
| 2 | **Nguyễn Thanh Huyền** | 23120049 |
| 3 | **Lê Nhật Thành** | 23120357 |

---

## 🏗️ Kiến trúc Hệ thống & Nguyên lý Hoạt động

Hệ thống hoạt động dựa trên mô hình **IP Multicast** truyền thông một-nhiều (One-to-Many):

```text
                       +-------------------------+
                       |   Server (Phát video)   |
                       +------------+------------+
                                    | UDP Multicast Packets
                                    v
                     +-----------------------------+
                     | Multicast Group: 239.1.1.1  |
                     | Port: 5004                  |
                     +--------------+--------------+
                                    |
         +--------------------------+--------------------------+
         |                          |                          |
         v                          v                          v
+--------+--------+        +--------+--------+        +--------+--------+
|    Client 1     |        |    Client 2     |        |    Client 3     |
| (Nhận & Hiển thị)|       | (Nhận & Hiển thị)|       | (Nhận & Hiển thị)|
+-----------------+        +-----------------+        +-----------------+
```

💻 Hướng dẫn Cài đặt & Khởi chạy Hệ thống
-----------------------------------------

### 🛠️ Điều kiện tiên quyết

Đảm bảo máy đã cài đặt Python 3 và thư viện xử lý ảnh thư viện Pillow. Nếu chưa có, hãy cài đặt bằng lệnh:

Bash
```
pip install Pillow
```

### 🚀 Các bước khởi chạy hệ thống

Hệ thống hỗ trợ chạy nhiều Client đồng thời. Hãy mở các Terminal riêng biệt và thực hiện theo thứ tự sau:

#### Bước 1: Khởi chạy Máy chủ (Server)

Mở một terminal mới, chuyển hướng vào thư mục chứa dự án và chạy câu lệnh sau để bắt đầu phát video (thay bằng đường dẫn tới file video .mjpeg):

Bash
```
python Server.py
```

_Ví dụ:_ python Server.py video.mjpeg

#### Bước 2: Khởi chạy Máy khách thứ nhất (Client 1)

Mở một terminal thứ hai và khởi chạy giao diện người dùng Client 1:

Bash

```
python Client.py
```

_Ví dụ:python Client.py   `

Nhấp vào nút **"Join Stream"** trên giao diện GUI để gia nhập nhóm và xem video trực tuyến.

#### Bước 3: Khởi chạy Máy khách thứ hai (Client 2)

Mở một terminal thứ ba (New Terminal) để khởi chạy một thực thể Client độc lập tiếp theo:

Bash
```
python Client.py
```

Nhấp nút **"Join Stream"** để kiểm chứng khả năng nhận luồng đồng thời (Concurrency) của mạng Multicast.

#### Bước 4: Khởi chạy thêm các Máy khách khác (Client N...)

Ta có thể mở thêm bao nhiêu Terminal tùy ý để chạy thêm các Client:

Bash
```
python Client.py
```