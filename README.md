# 📦 Parcel Tracking Telegram Bot

Bot Telegram theo dõi trạng thái đơn hàng từ nhiều đơn vị vận chuyển — tự động cập nhật mỗi 5 phút.

[![Telegram Bot](https://img.shields.io/badge/Telegram-@shippingtrackers__bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/shippingtrackers_bot)

## ✨ Tính năng

- 🚚 Theo dõi đơn hàng từ **3 đơn vị vận chuyển**
- 🔔 Tự động thông báo khi trạng thái thay đổi
- 📜 Xem lịch sử vận chuyển chi tiết với timeline
- 🌍 Hỗ trợ 3 ngôn ngữ: Tiếng Việt, English, 日本語
- ⚡ **Auto-add**: Chỉ cần gửi mã tracking, bot tự động thêm

## 📦 Nhà vận chuyển hỗ trợ

| Đơn vị | Format mã | Ví dụ | Auto-detect |
|--------|-----------|-------|-------------|
| **Shopee Express** | `SPX*`, `SLS*` | `SPXVN123456789` | ✅ |
| **JT Express** | `JT*` hoặc 10-15 số | `JT123456789` | ✅ |
| **Giao Hàng Nhanh** | 8 ký tự alphanumeric | `GYWFRP6T` | ✅ |

## 🚀 Chạy với Docker

### Từ Docker Hub / GHCR

```bash
# Pull image từ GitHub Container Registry
docker pull ghcr.io/sson6926/parcel-tracking-telegram-bot:latest

# Hoặc dùng docker-compose
version: '3.8'
services:
  bot:
    image: ghcr.io/sson6926/parcel-tracking-telegram-bot:latest
    env_file: .env
    restart: unless-stopped
```

### Build từ source

```bash
# 1. Clone repository
git clone https://github.com/sson6926/Parcel-Tracking-Telegram-Bot.git
cd Parcel-Tracking-Telegram-Bot

# 2. Cấu hình môi trường
cp .env.example .env
# Sửa BOT_TOKEN và DATABASE_URL trong .env

# 3. Khởi động
docker compose up -d

# 4. Xem logs
docker compose logs -f bot
```

## ⚙️ Biến môi trường

| Biến | Bắt buộc | Mặc định | Mô tả |
|------|----------|----------|-------|
| `BOT_TOKEN` | ✅ | — | Telegram Bot Token từ [@BotFather](https://t.me/BotFather) |
| `DATABASE_URL` | ✅ khi deploy | `sqlite:///tracking.db` | Chuỗi kết nối database ngoài |
| `CHECK_INTERVAL_MINUTES` | | `5` | Tần suất kiểm tra cập nhật (phút) |
| `LOG_LEVEL` | | `INFO` | Mức độ log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `SENTRY_DSN` | | — | Sentry DSN cho error tracking (tuỳ chọn) |

## 📱 Cách sử dụng

### Thêm đơn hàng

**Cách 1: Auto-add (Nhanh nhất)**
```
Chỉ cần gửi mã tracking vào chat:
GYWFRP6T
SPXVN123456789
JT123456789
```

**Cách 2: Dùng lệnh**
```
/add → Chọn đơn vị vận chuyển → Nhập mã
```

### Lệnh khác

| Lệnh | Mô tả |
|------|-------|
| `/start` | Hiển thị menu chính |
| `/list` | Xem danh sách đơn hàng đang theo dõi |
| `/remove` | Xóa đơn hàng khỏi danh sách |
| `/lang` | Thay đổi ngôn ngữ giao diện |
| `/help` | Xem hướng dẫn chi tiết |

## 🏗️ Kiến trúc

Project được xây dựng theo **Clean Architecture** với các layer rõ ràng:

```
app/
├── handlers/          # UI layer - Telegram handlers
├── services/          # Business logic layer
├── providers/         # External API integrations
│   ├── shopeeexpress/
│   ├── jtexpress/
│   └── ghn/
├── models/            # Database models
├── database/          # Database infrastructure
├── i18n/              # Internationalization
└── utils/             # Shared utilities
```

Xem chi tiết trong [ARCHITECTURE.md](ARCHITECTURE.md)

## 🔧 Development

### Yêu cầu
- Python 3.9+
- Docker & Docker Compose (cho deployment)

### Cài đặt local

```bash
# 1. Tạo virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# hoặc .venv\Scripts\activate  # Windows

# 2. Cài dependencies
pip install -r requirements.txt

# 3. Chạy bot
python -m app.main
```

### Thêm đơn vị vận chuyển mới

Xem hướng dẫn chi tiết trong [ARCHITECTURE.md - Adding a New Carrier](ARCHITECTURE.md#adding-a-new-carrier)

## 📊 Database

Bot hỗ trợ cả SQLite và MySQL:

**SQLite (mặc định - cho development):**
```env
DATABASE_URL=sqlite:///tracking.db
```

**MySQL service ngoài (khuyến khích cho production):**
```env
DATABASE_URL=mysql+pymysql://user:password@mysql.example.com:3306/tracking_db
```

Nếu username hoặc password có ký tự đặc biệt, cần URL-encode các giá trị đó. Docker Compose chỉ chạy bot và không khởi tạo MySQL nội bộ.

**Azure Database for MySQL:**
```env
DATABASE_URL=mysql+pymysql://user:password@server.mysql.database.azure.com:3306/tracking_db?ssl_ca=/etc/ssl/certs/ca-certificates.crt
```

## ☁️ Deployment Options

### Docker Compose (Recommended for VPS)
```bash
# DATABASE_URL trong .env phải trỏ tới database service ngoài
docker compose up -d
```

### Azure Container Apps (Serverless)
Xem hướng dẫn chi tiết: [docs/AZURE_DEPLOYMENT.md](docs/AZURE_DEPLOYMENT.md)

**Ưu điểm:**
- ✅ Không cần quản lý VM
- ✅ Auto-scaling
- ✅ Pay-per-use (~$20-30/month)
- ✅ Managed database (Azure MySQL)

**Quick deploy:**
```bash
az containerapp create \
  --name telegram-bot \
  --resource-group rg-telegram-bot \
  --image ghcr.io/sson6926/parcel-tracking-telegram-bot:latest \
  --environment env-telegram-bot \
  --secrets bot-token="YOUR_TOKEN" \
  --env-vars "BOT_TOKEN=secretref:bot-token"
```

## 🐛 Troubleshooting

### Bot không phản hồi
```bash
# Kiểm tra logs
docker compose logs -f bot

# Restart bot
docker compose restart bot
```

### Database errors
```bash
# Kiểm tra chuỗi kết nối database ngoài và logs của bot
docker compose logs --tail=100 bot
```

### Conflict error
```
Conflict: terminated by other getUpdates request
```
→ Có instance khác đang chạy. Stop tất cả instances trước khi start lại.

## 📝 License

MIT License - Xem [LICENSE](LICENSE) để biết thêm chi tiết.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 Contact

- Telegram: [@shippingtrackers_bot](https://t.me/shippingtrackers_bot)
- GitHub: [@sson6926](https://github.com/sson6926)

---

⭐ Nếu project hữu ích, hãy cho một star nhé!
