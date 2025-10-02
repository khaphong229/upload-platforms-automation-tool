# TikTok Upload Manager

Công cụ quản lý và tự động đăng video lên TikTok với nhiều tài khoản, lập lịch đăng bài và giao diện thân thiện.

## Tính năng chính

- 🚀 Đăng video lên nhiều tài khoản TikTok cùng lúc
- 📅 Lập lịch đăng bài tự động
- 👤 Quản lý nhiều tài khoản dễ dàng
- 🎬 Xem trước video trước khi đăng
- 🏷️ Quản lý hashtag và mô tả
- 📊 Theo dõi trạng thái đăng tải
- 🔒 Đăng nhập an toàn với lưu phiên làm việc
- 📝 Tạo blog post tự động với Google Gemini AI
- 🔗 Rút gọn link APK tự động
- 📺 Tải video từ YouTube hoặc sử dụng file local

## Cài đặt

1. Clone repository
2. Cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

3. Tạo thư mục cấu hình:

```bash
mkdir -p ~/.tiktok_profiles
```

4. Cài đặt Chrome và ChromeDriver (nếu chưa có)
5. Cấu hình file `.env` với các API keys cần thiết

## Hướng dẫn sử dụng

### Chương trình tích hợp (Khuyến nghị)

```bash
python main_integrated.py
```

Chương trình này bao gồm cả hai chức năng:
- **Content Distribution**: Tải video từ YouTube, tạo blog, upload lên TikTok
- **Batch Upload**: Upload video lên nhiều tài khoản TikTok cùng lúc

### Khởi động từng chức năng riêng biệt

#### 1. Content Distribution (Phân phối nội dung)
```bash
python gui_main.py
```

#### 2. Batch Upload (Upload hàng loạt)
```bash
python run_batch_uploader.py
# hoặc
run_batch_uploader.bat
```

#### 3. Command Line Interface
```bash
python main.py --youtube-url "https://www.youtube.com/watch?v=example" --title "My App Title" --apk-links "https://example.com/app1.apk"
```

### Quản lý tài khoản TikTok

1. Mở tab "Batch Upload" hoặc chạy batch uploader
2. Nhấn "Add Profile" để thêm tài khoản mới
3. Nhập tên profile và nhấn "Add"
4. Đăng nhập vào tài khoản TikTok trong cửa sổ trình duyệt
5. Cấu hình video cho từng tài khoản
6. Chọn tài khoản và nhấn "Upload Selected Profiles"

### Cấu hình video cho batch upload

1. Chọn profile trong danh sách
2. Nhấn "Configure Video"
3. Chọn file video, nhập caption và hashtags
4. Nhấn "Save Configuration"
5. Lặp lại cho các profile khác
6. Chọn các profile đã cấu hình và nhấn "Upload Selected Profiles"

## Cấu trúc thư mục

```
├── main.py                     # CLI entry point
├── gui_main.py                 # Content Distribution GUI
├── main_integrated.py          # Integrated GUI (All features)
├── run_batch_uploader.py       # Batch Upload standalone
├── config/                     # Cấu hình
├── services/                   # Các service chính
│   ├── youtube/               # Service tải video YouTube
│   ├── shortener/             # Service rút gọn link
│   ├── ai/                    # Service tạo nội dung với AI
│   ├── blogger/               # Service đăng bài lên Blogger
│   └── tiktok/                # Service đăng video lên TikTok
├── batch_uploader/            # Hệ thống upload hàng loạt
│   ├── gui/                   # GUI components
│   ├── tiktok_uploader/       # Upload logic
│   └── core/                  # Account management
├── utils/                     # Tiện ích
└── requirements.txt           # Dependencies
```

## Lưu ý

- Cần có tài khoản Google với quyền truy cập Blogger API
- Cần có tài khoản TikTok
- Đảm bảo tuân thủ điều khoản sử dụng của các platform
- API của Google Gemini có giới hạn sử dụng miễn phí, kiểm tra hạn mức sử dụng trên trang Google AI Studio

## Phát triển thêm

- Thêm hỗ trợ cho WordPress
- Thêm tính năng lên lịch đăng bài
- Thêm tính năng theo dõi hiệu suất
- Thêm giao diện người dùng (GUI)

## Giấy phép

MIT License
