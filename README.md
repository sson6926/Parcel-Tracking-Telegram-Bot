# 📦 Parcel Tracking Telegram Bot

Bot Telegram theo dõi trạng thái đơn hàng từ Shopee Express và JT Express — tự động cập nhật mỗi 5 phút.

[![Telegram Bot](https://img.shields.io/badge/Telegram-@shippingtrackers__bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/shippingtrackers_bot)

## Tính năng

- Theo dõi đơn hàng Shopee Express & JT Express
- Tự động thông báo khi trạng thái thay đổi
- Xem lịch sử vận chuyển chi tiết
- Hỗ trợ 3 ngôn ngữ: Tiếng Việt, English, 日本語

## Chạy với Docker

```bash
# 1. Clone
git clone https://github.com/sson6926/Parcel-Tracking-Telegram-Bot.git
cd Parcel-Tracking-Telegram-Bot

# 2. Cấu hình .env
cp .env .env.local  # sửa BOT_TOKEN

# 3. Chạy
docker compose up -d
```

## Biến môi trường

| Biến | Bắt buộc | Mặc định | Mô tả |
|------|----------|----------|-------|
| `BOT_TOKEN` | ✅ | — | Telegram Bot Token |
| `DATABASE_URL` | | `sqlite:///tracking.db` | Chuỗi kết nối DB |
| `CHECK_INTERVAL_MINUTES` | | `5` | Tần suất kiểm tra (phút) |
| `LOG_LEVEL` | | `INFO` | Mức log |
| `SENTRY_DSN` | | — | Error tracking (tuỳ chọn) |

## Lệnh

| Lệnh | Mô tả |
|------|-------|
| `/start` | Menu chính |
| `/add` | Thêm đơn hàng |
| `/list` | Danh sách đơn hàng |
| `/remove` | Xóa đơn hàng |
| `/lang` | Đổi ngôn ngữ |
| `/help` | Trợ giúp |

## Nhà vận chuyển hỗ trợ

- **Shopee Express** — mã bắt đầu bằng `SPXVN`
- **JT Express** — mã bắt đầu bằng `JT` hoặc số
