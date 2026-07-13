#!/bin/bash
# Test webhook với ngrok
# Chạy script này để test webhook mode với ngrok

set -e

echo "🚀 Testing Webhook with ngrok"
echo "================================"
echo ""

# Kiểm tra ngrok có được cài đặt không
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok không được tìm thấy. Vui lòng cài đặt ngrok từ https://ngrok.com/"
    exit 1
fi

# Kiểm tra BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
    else
        echo "❌ Không tìm thấy BOT_TOKEN. Vui lòng set BOT_TOKEN hoặc tạo file .env"
        exit 1
    fi
fi

echo "📝 Hướng dẫn:"
echo "1. Mở terminal mới và chạy: ngrok http 8443"
echo "2. Copy HTTPS URL từ ngrok (ví dụ: https://abc123.ngrok.io)"
echo "3. Nhập URL đó vào prompt bên dưới"
echo ""

# Nhập ngrok URL
read -p "Nhập ngrok HTTPS URL (hoặc Enter để dùng webhook URL từ .env): " NGROK_URL

if [ -z "$NGROK_URL" ]; then
    NGROK_URL=$WEBHOOK_URL
fi

if [ -z "$NGROK_URL" ]; then
    echo "❌ Không có webhook URL. Vui lòng nhập URL hoặc set WEBHOOK_URL trong .env"
    exit 1
fi

echo ""
echo "✅ Sử dụng webhook URL: $NGROK_URL"
echo ""

# Tạo file .env.test
cat > .env.test << EOF
BOT_MODE=webhook
WEBHOOK_URL=$NGROK_URL
WEBHOOK_PATH=/webhook
WEBHOOK_PORT=8443
WEBHOOK_SECRET=test_secret_$(openssl rand -hex 8)
BOT_TOKEN=$BOT_TOKEN
DATABASE_URL=${DATABASE_URL:-sqlite:///tracking.db}
CHECK_INTERVAL_MINUTES=${CHECK_INTERVAL_MINUTES:-5}
LOG_LEVEL=INFO
DEFAULT_LANG=vi
EOF

echo "✅ Đã tạo file .env.test với cấu hình webhook"
echo ""

# Hiển thị cấu hình
echo "📋 Cấu hình webhook:"
echo "-------------------"
grep -E "BOT_MODE|WEBHOOK_URL|WEBHOOK_PATH|WEBHOOK_PORT|WEBHOOK_SECRET" .env.test | sed 's/WEBHOOK_SECRET=.*/WEBHOOK_SECRET=***hidden***/'
echo ""

# Test health check
echo "🔍 Kiểm tra bot đang chạy..."
if curl -s http://localhost:8443/health > /dev/null 2>&1; then
    echo "✅ Bot đang chạy trên port 8443"
else
    echo "⚠️  Bot chưa chạy trên port 8443"
    echo "   Vui lòng chạy: docker-compose --env-file .env.test up"
fi
echo ""

# Kiểm tra webhook info
echo "🔍 Kiểm tra trạng thái webhook từ Telegram..."
WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo")
echo "$WEBHOOK_INFO" | python3 -m json.tool 2>/dev/null || echo "$WEBHOOK_INFO"
echo ""

# Test set webhook
read -p "Bạn có muốn set webhook ngay không? (y/n): " SET_WEBHOOK

if [ "$SET_WEBHOOK" = "y" ] || [ "$SET_WEBHOOK" = "Y" ]; then
    WEBHOOK_SECRET=$(grep WEBHOOK_SECRET .env.test | cut -d'=' -f2)
    FULL_WEBHOOK_URL="$NGROK_URL/webhook"
    
    echo "🔧 Setting webhook to: $FULL_WEBHOOK_URL"
    
    SET_RESULT=$(curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
        -d "url=$FULL_WEBHOOK_URL" \
        -d "secret_token=$WEBHOOK_SECRET" \
        -d "drop_pending_updates=true" \
        -d "allowed_updates=[\"message\",\"callback_query\"]")
    
    echo "$SET_RESULT" | python3 -m json.tool 2>/dev/null || echo "$SET_RESULT"
    
    if echo "$SET_RESULT" | grep -q '"ok":true'; then
        echo ""
        echo "✅ Webhook đã được set thành công!"
    else
        echo ""
        echo "❌ Lỗi khi set webhook"
    fi
fi

echo ""
echo "📚 Các bước tiếp theo:"
echo "1. Nếu bot chưa chạy: docker-compose --env-file .env.test up"
echo "2. Gửi tin nhắn cho bot trên Telegram"
echo "3. Kiểm tra logs: docker-compose logs -f bot"
echo "4. Kiểm tra ngrok dashboard: http://localhost:4040"
echo ""
echo "🧹 Để xóa webhook: curl -X POST https://api.telegram.org/bot\$BOT_TOKEN/deleteWebhook"
echo ""