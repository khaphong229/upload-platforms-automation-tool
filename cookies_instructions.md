# Hướng dẫn lấy cookies.txt cho TikTok

## Phương pháp 1: Sử dụng Extension "Get cookies.txt" (Khuyến nghị)

### Bước 1: Cài đặt Extension
1. Mở Chrome và truy cập [Chrome Web Store](https://chrome.google.com/webstore)
2. Tìm kiếm "Get cookies.txt"
3. Cài đặt extension "Get cookies.txt"

### Bước 2: Lấy cookies
1. Truy cập [TikTok.com](https://www.tiktok.com) và **đăng nhập** tài khoản của bạn
2. Click vào icon extension "🍪 Get cookies.txt" trên thanh công cụ
3. Click **"Export As ⇩"**
4. Lưu file với tên `cookies.txt` vào thư mục gốc của project

## Phương pháp 2: Sử dụng Developer Tools

### Bước 1: Mở Developer Tools
1. Truy cập [TikTok.com](https://www.tiktok.com) và đăng nhập
2. Nhấn **F12** để mở Developer Tools
3. Chọn tab **"Application"** (hoặc "Storage")

### Bước 2: Lấy sessionid
1. Bên trái chọn **"Cookies"** → **"https://www.tiktok.com"**
2. Tìm cookie có tên **"sessionid"**
3. Copy giá trị (Value) của cookie này

### Bước 3: Tạo cookies.txt thủ công
Tạo file `cookies.txt` với nội dung:
```
# Netscape HTTP Cookie File
.tiktok.com	TRUE	/	FALSE	0	sessionid	[YOUR_SESSIONID_VALUE]
```

## Phương pháp 3: Sử dụng cookies_list trong code

Nếu bạn chỉ có sessionid, có thể sử dụng trực tiếp trong code:

```python
from services.tiktok import NewTikTokUploader

# Tạo cookies list từ sessionid
sessionid = "your_sessionid_value_here"
tiktok = NewTikTokUploader()
cookies_list = tiktok.create_cookies_list_from_sessionid(sessionid)

# Sử dụng cookies_list
uploader = NewTikTokUploader(cookies_list=cookies_list)
```

## Lưu ý quan trọng:

⚠️ **Bảo mật:**
- Không chia sẻ file cookies.txt hoặc sessionid với người khác
- Thêm `cookies.txt` vào file `.gitignore`

⚠️ **Hết hạn:**
- Cookies sẽ hết hạn sau một thời gian
- Nếu upload thất bại, hãy lấy cookies mới

⚠️ **Vị trí file:**
- Đặt file `cookies.txt` ở thư mục gốc của project (cùng cấp với `run_gui.py`)

## Kiểm tra file cookies.txt

File `cookies.txt` hợp lệ sẽ có dạng:
```
# Netscape HTTP Cookie File
.tiktok.com	TRUE	/	FALSE	1735689600	sessionid	abc123xyz...
.tiktok.com	TRUE	/	FALSE	1735689600	csrf_token	def456uvw...
```

Sau khi có file `cookies.txt`, bạn có thể chạy ứng dụng và upload video lên TikTok!
