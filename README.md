# Auto Content Distribution Tool

Tool tự động hóa quy trình phân phối nội dung từ YouTube sang Blogger và TikTok.

## Tính năng

- Tải video từ YouTube
- Rút gọn link APK
- Tạo bài viết blog tự động với Google Gemini AI (miễn phí)
- Đăng video lên TikTok
- Tự động thêm link blog vào caption và comment

## Cài đặt

1. Clone repository
2. Cài đặt dependencies:

```bash
pip install -r requirements.txt
```

3. Tạo file `.env` từ file `.env.example` và thêm các thông tin cần thiết:

```bash
cp .env.example .env
# Sau đó chỉnh sửa file .env với thông tin của bạn
```

4. Lấy API Key của Google Gemini:

   - Truy cập [Google AI Studio](https://aistudio.google.com/)
   - Đăng ký hoặc đăng nhập vào tài khoản Google
   - Trong trang chủ, tìm phần "API keys" và tạo API key mới
   - Sao chép API key và thêm vào file .env

5. Cấu hình OAuth cho Blogger:
   - Tạo project trong [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Blogger API
   - Tạo OAuth credentials (Web application)
   - Lấy Client ID và Client Secret
   - Sử dụng OAuth Playground để lấy refresh token:
     - Truy cập [OAuth Playground](https://developers.google.com/oauthplayground/)
     - Chọn Blogger API v3
     - Authorize APIs
     - Exchange authorization code for tokens
     - Lưu refresh token vào file .env

## Sử dụng

1. Chạy tool:

```bash
python main.py
```

2. Nhập thông tin cần thiết:

   - Link video YouTube
   - Tiêu đề video
   - Các link APK

3. Hoặc sử dụng command line arguments:

```bash
python main.py --youtube-url "https://www.youtube.com/watch?v=example" --title "My App Title" --apk-links "https://example.com/app1.apk" "https://example.com/app2.apk"
```

4. Các tùy chọn khác:

```bash
python main.py --help
```

## Quy trình hoạt động

1. Tải video từ YouTube
2. Rút gọn các link APK
3. Tạo bài viết blog với nội dung được tạo bởi Google Gemini AI
4. Đăng video lên TikTok với caption và comment chứa link blog

## Cấu trúc thư mục

```
├── main.py                 # Entry point
├── config/                 # Cấu hình
│   ├── __init__.py
│   └── config.py
├── services/               # Các service chính
│   ├── youtube/            # Service tải video YouTube
│   ├── shortener/          # Service rút gọn link
│   ├── ai/                 # Service tạo nội dung với Google Gemini AI
│   ├── blogger/            # Service đăng bài lên Blogger
│   └── tiktok/             # Service đăng video lên TikTok
├── utils/                  # Tiện ích
│   ├── __init__.py
│   └── helpers.py
├── .env                    # Environment variables
├── .env.example            # Environment variables template
└── requirements.txt        # Dependencies
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
