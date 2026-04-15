# Tracking Shopee - Telegram Bot

Bot Telegram để theo dõi trạng thái đơn hàng từ các hệ thống vận chuyển khác nhau (Shopee Express, JT Express)
Check it out: @shippingtrackers_bot on Telegram

## Tính năng

- ✅ Thêm theo dõi đơn hàng từ nhiều hãng vận chuyển
- ✅ Xem chi tiết đơn hàng và lịch sử vận chuyển
- ✅ Phân trang cho lịch sử vận chuyển
- ✅ Hỗ trợ múi ngôn ngữ (Tiếng Việt, English, 日本語)
- ✅ Xóa đơn hàng đã theo dõi
- ✅ Cập nhật trạng thái tự động mỗi 5 phút

## Cài đặt

### 1. Clone Repository
```bash
git clone <repository-url>
cd "Tracking Shopee"
```

### 2. Tạo Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Cài đặt Dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu hình Environment Variables
```bash
cp .env.example .env
# Sửa .env và thêm BOT_TOKEN của bạn
```

### 5. Chạy Bot
```bash
python3 -m bot.main
```

## Cấu hình

### Biến Environment

- `BOT_TOKEN` - Telegram Bot Token (bắt buộc)
- `DATABASE_URL` - Chuỗi kết nối database (Mặc định: `sqlite:///./tracking.db`)
- `LOG_LEVEL` - Mức độ ghi log (Mặc định: `INFO`)
- `CHECK_INTERVAL_MINUTES` - Khoảng thời gian cập nhật (Mặc định: `5`)
- `DEFAULT_LANG` - Ngôn ngữ mặc định (Mặc định: `vi`)

## Cấu trúc Dự án

```
.
├── app/
│   ├── bot/
│   │   └── handlers.py       # Xử lý lệnh và callback Telegram
│   ├── core/
│   │   └── i18n.py           # Hỗ trợ quốc tế hóa
│   └── i18n/                 # Tệp dịch (vi, en, ja)
├── bot/
│   └── main.py               # Điểm vào chương trình
├── db/
│   ├── __init__.py           # Cấu hình database
│   ├── database.py           # Tương thích với phiên bản cũ
│   └── models.py             # Models SQLAlchemy
├── tracking/
│   ├── types.py              # Kiểu dữ liệu và enums
│   ├── parsers.py            # Logic phân tích trạng thái
│   ├── service.py            # Logic kinh doanh
│   ├── scheduler.py          # Lập lịch công việc nền
│   └── providers/            # Các trình cung cấp theo dõi
│       ├── base.py
│       ├── shopeeexpress.py
│       ├── jtexpress.py
│       └── __init__.py
├── requirements.txt
├── Procfile
└── README.md
```

## Lệnh Telegram

- `/start` - Menu chính
- `/list` - Xem danh sách đơn hàng
- `/add` - Thêm đơn hàng mới
- `/remove` - Xóa đơn hàng
- `/help` - Xem trợ giúp
- `/lang` - Thay đổi ngôn ngữ

## Cấu trúc Cơ sở dữ liệu

### Users
- `telegram_chat_id` - ID chat của người dùng
- `created_at` - Ngày tạo

### Carriers
- `code` - Mã code (jtexpress, shopeeexpress)
- `name` - Tên công ty

### Tracking
- `user_id` - Người dùng sở hữu
- `carrier_id` - Hãng vận chuyển
- `tracking_code` - Mã theo dõi
- `last_status` - Trạng thái cuối
- `next_check_at` - Lần cập nhật tiếp theo
- `is_active` - Trạng thái hoạt động

### TrackingEvents
- `tracking_id` - Mã theo dõi
- `status` - Trạng thái (CREATED, PICKED_UP, IN_TRANSIT, v.v.)
- `description` - Mô tả
- `location` - Vị trí
- `event_time` - Thời gian sự kiện
- `event_hash` - Hash để loại bỏ trùng lặp

## Nhà cung cấp được hỗ trợ

- Shopee Express - Qua spx.vn API
- JT Express - Qua HTML parsing

## Giấy phép

MIT License

## Câu hỏi thường gặp

### Bot không phản hồi
- Kiểm tra BOT_TOKEN có được cấu hình đúng
- Kiểm tra kết nối Internet

### Trạng thái không cập nhật
- Kiểm tra `CHECK_INTERVAL_MINUTES` có được đặt hợp lý
- Kiểm tra logs để xem lỗi

### Mã theo dõi không hợp lệ
- Sử dụng mã từ Shopee Express (SPX...) hoặc JT Express
- Kiểm tra xem mã có bị sai không

