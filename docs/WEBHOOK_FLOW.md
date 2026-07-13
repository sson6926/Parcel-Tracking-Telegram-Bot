# Webhook Flow - Cách hoạt động của Webhook Mode

## Sơ đồ Luồng Webhook

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          WEBHOOK MODE FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

1. BOT STARTUP (Khởi động bot)
   ┌──────────────────────┐
   │  Bot starts (main)   │
   └──────────┬───────────┘
              │
              ▼
   ┌──────────────────────────────────────────┐
   │ Check BOT_MODE == "webhook"              │
   │ YES → Call start_webhook()               │
   └──────────┬───────────────────────────────┘
              │
              ▼
   ┌──────────────────────────────────────────┐
   │ Create aiohttp web server                │
   │ Listen on 0.0.0.0:WEBHOOK_PORT (8443)   │
   └──────────┬───────────────────────────────┘
              │
              ▼
   ┌──────────────────────────────────────────┐
   │ Register webhook endpoint /webhook       │
   │ Register health check /health            │
   └──────────┬───────────────────────────────┘
              │
              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ Call bot.set_webhook(url, secret_token, drop_pending=True)  │
   │                                                               │
   │ Telegram API:                                                │
   │ POST /setWebhook                                             │
   │ url=https://yourdomain.com/webhook                           │
   │ secret_token=your_secret_here                               │
   └──────────┬───────────────────────────────────────────────────┘
              │
              ▼
   ┌─────────────────────────────────────────────┐
   │ ✅ Bot ready to receive webhook updates     │
   │ Waiting for messages from users...          │
   └─────────────────────────────────────────────┘


2. USER SENDS MESSAGE (Người dùng gửi tin nhắn)
   ┌──────────────────────┐
   │  User on Telegram    │
   │   Types message:     │
   │   "SPXVN123456789"   │
   └──────────┬───────────┘
              │
              ▼ (via internet)
   ┌──────────────────────────────────────────────┐
   │ Telegram Servers                             │
   │ (Process message, create Update object)      │
   └──────────┬───────────────────────────────────┘
              │
              ▼ (HTTPS POST request)
   ┌──────────────────────────────────────────────────────────────┐
   │ POST https://yourdomain.com/webhook                          │
   │                                                               │
   │ Headers:                                                     │
   │   Content-Type: application/json                            │
   │   X-Telegram-Bot-Api-Secret-Token: your_secret_here        │
   │                                                               │
   │ Body (Update JSON):                                         │
   │ {                                                            │
   │   "update_id": 123456789,                                   │
   │   "message": {                                              │
   │     "message_id": 456,                                      │
   │     "from": {"id": 12345, "first_name": "John"},           │
   │     "chat": {"id": 12345, "type": "private"},              │
   │     "date": 1626190000,                                    │
   │     "text": "SPXVN123456789"                               │
   │   }                                                         │
   │ }                                                            │
   └──────────┬───────────────────────────────────────────────────┘
              │
              ▼ (via internet)


3. BOT RECEIVES WEBHOOK (Bot nhận webhook)
   ┌────────────────────────────────────────┐
   │ aiohttp handler receives HTTP request  │
   │ handle_webhook(request)                │
   └──────────┬─────────────────────────────┘
              │
              ▼
   ┌────────────────────────────────────────────────────┐
   │ Verify secret token from header                    │
   │ X-Telegram-Bot-Api-Secret-Token == WEBHOOK_SECRET │
   │                                                     │
   │ If mismatch → Return 403 Forbidden ❌              │
   │ If match → Continue ✅                            │
   └──────────┬─────────────────────────────────────────┘
              │
              ▼
   ┌────────────────────────────────────────┐
   │ Parse JSON request body                │
   │ Create Update object from Telegram API │
   │ data                                   │
   └──────────┬─────────────────────────────┘
              │
              ▼
   ┌────────────────────────────────────────┐
   │ Call: await dp.feed_update(bot, update)│
   │                                         │
   │ Pass update to Dispatcher               │
   │ (Starts processing handlers)            │
   └──────────┬─────────────────────────────┘
              │
              ▼ (return immediately to Telegram)
   ┌────────────────────────────────────────┐
   │ Return 200 OK to Telegram               │
   │ (Acknowledge receipt)                   │
   └────────────────────────────────────────┘


4. DISPATCHER PROCESSES UPDATE (Xử lý Update)
   ┌────────────────────────────────────────────┐
   │ dp.feed_update() routes to handlers        │
   │                                             │
   │ Check message filters:                     │
   │ ✓ Is TEXT? ✓ Not COMMAND? → Match handler │
   └──────────┬─────────────────────────────────┘
              │
              ▼
   ┌────────────────────────────────────────────┐
   │ Find matching handler (pattern matching)   │
   │                                             │
   │ For "SPXVN123456789":                     │
   │ → auto_add_from_message()                 │
   │   (regex: ^\d{15}$|^(SPX|SLS)[A-Z0-9]+$)  │
   └──────────┬─────────────────────────────────┘
              │
              ▼
   ┌────────────────────────────────────────────┐
   │ Execute handler with context:              │
   │ - update object                            │
   │ - user_id, chat_id                         │
   │ - message text                             │
   │ - bot instance (for sending messages)      │
   └──────────┬─────────────────────────────────┘
              │
              ▼
   ┌────────────────────────────────────────────┐
   │ Handler logic:                             │
   │ 1. Parse tracking number                   │
   │ 2. Detect carrier                          │
   │ 3. Save to database                        │
   │ 4. Fetch tracking info from provider       │
   │ 5. Format response message                 │
   └──────────┬─────────────────────────────────┘
              │
              ▼


5. BOT SENDS RESPONSE (Bot gửi phản hồi)
   ┌──────────────────────────────────────────┐
   │ Call: await update.message.reply_text()  │
   │                                           │
   │ Text: "✅ Added tracking"                │
   └──────────┬────────────────────────────────┘
              │
              ▼ (HTTPS request to Telegram API)
   ┌──────────────────────────────────────────────────────┐
   │ POST https://api.telegram.org/bot123456:TOKEN        │
   │ /sendMessage                                         │
   │                                                       │
   │ Parameters:                                          │
   │ - chat_id: 12345                                    │
   │ - text: "✅ Added tracking SPXVN123456789"          │
   │ - parse_mode: HTML                                  │
   │ - reply_markup: buttons/keyboard (if any)           │
   └──────────┬───────────────────────────────────────────┘
              │
              ▼ (via internet)
   ┌──────────────────────────────────────────┐
   │ Telegram Servers                         │
   │ Send message to user                     │
   └──────────┬────────────────────────────────┘
              │
              ▼
   ┌──────────────────────────────────────────┐
   │ User receives response in Telegram       │
   │ Chat shows: "✅ Added tracking..."       │
   └──────────────────────────────────────────┘


6. BACKGROUND UPDATES (Cập nhật nền - từ Scheduler)
   ┌────────────────────────────────────────┐
   │ TrackingScheduler runs every 5 minutes │
   │ (configured via CHECK_INTERVAL_MINUTES)│
   └──────────┬──────────────────────────────┘
              │
              ▼
   ┌────────────────────────────────────────┐
   │ Check all tracked orders for updates   │
   │ (Database query)                       │
   └──────────┬──────────────────────────────┘
              │
              ▼
   ┌────────────────────────────────────────┐
   │ For each order:                        │
   │ - Call carrier provider API            │
   │ - Get latest tracking status           │
   │ - Compare with stored status           │
   │ - If changed → Send user notification  │
   └──────────┬──────────────────────────────┘
              │
              ▼
   ┌────────────────────────────────────────────────┐
   │ Call: await bot.send_message()                │
   │ (Same as step 5, sends via Telegram Bot API) │
   └────────────────────────────────────────────────┘
```

## Sequence Diagram

```
User              Telegram        Bot (Webhook)       Telegram API
 │                    │                   │                 │
 │─ Send message     │                   │                 │
 ├───────────────────>│                   │                 │
 │                    │─ Create Update   │                 │
 │                    │─ POST /webhook  │                 │
 │                    ├──────────────────>│                 │
 │                    │                   │                 │
 │                    │                   │ Verify secret  │
 │                    │                   │ token ✓         │
 │                    │                   │                 │
 │                    │                   │ Parse JSON      │
 │                    │                   │ Feed to         │
 │                    │                   │ dispatcher      │
 │                    │<──────────────────│                 │
 │                    │ 200 OK            │                 │
 │                    │                   │                 │
 │                    │                   │ Call handlers   │
 │                    │                   │ Process logic   │
 │                    │                   │                 │
 │                    │                   │ Send response  │
 │                    │                   ├────────────────>│
 │                    │                   │ POST /          │
 │                    │                   │ sendMessage    │
 │                    │                   │                 │
 │<──────────────────────────────────────────────────────────│
 │       Receive message response         │                 │
 │                    │                   │                 │

```

## Comparison: Long Polling vs Webhook

| Aspek | Long Polling | Webhook |
|-------|--------------|---------|
| **Kiến trúc** | Bot chủ động request | Telegram chủ động push |
| **Latency** | 25-30 seconds (delay) | Real-time (< 1 second) |
| **Bandwidth** | Cao (requests liên tục) | Thấp (chỉ khi có update) |
| **Công khai URL** | Không cần | Cần |
| **SSL Certificate** | Không bắt buộc | **Bắt buộc** |
| **Public Port** | Không cần | Cần (8443, 443, 80, 88) |
| **Firewall NAT** | Hoạt động sau | Cần port forward |
| **Development** | ✅ Dễ | ❌ Phức tạp |
| **Production** | ❌ Chậm, tốn resource | ✅ Tối ưu |

## Key Benefits of Webhook

### 1. **Real-time Updates** ⚡
- User nhập tin nhắn → Bot nhận ngay (< 1 giây)
- So sánh Long Polling: Delay 25-30 seconds

### 2. **Lower Resource Usage** 💾
```
Long Polling: Bot makes request every ~30 seconds
Webhook: Bot chỉ wake up khi có message

Ví dụ cho 1000 users:
- Long Polling: ~2000 API calls/minute
- Webhook: 100-200 API calls/minute (depending on user activity)
```

### 3. **Scalability** 📈
```
Long Polling: Phải scale horizontally
- Problem: Multiple instances → Conflict errors
- Solution: Redis/Memcached for state sharing

Webhook: Các request độc lập
- Dễ dàng scale (load balancer)
- Không cần state sharing
```

### 4. **Cost Optimization** 💰
- Ít API calls → Giảm bandwidth
- Ít CPU usage → Giảm server costs
- Azure: ~50-70% tiết kiệm so với long polling

## Troubleshooting Webhook

### Problem: "Webhook set but updates not received"

**Kiểm tra:**
```bash
# 1. Verify webhook is set
curl https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo

# Expected response:
{
  "ok": true,
  "result": {
    "url": "https://yourdomain.com/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "ip_address": "123.45.67.89",
    "last_error_date": null
  }
}
```

### Problem: "SSL certificate error"

```bash
# Telegram chỉ chấp nhận:
# - Let's Encrypt (free)
# - DigiCert, Comodo, etc. (paid)
# - KHÔNG chấp nhận self-signed certificates

# Verify certificate:
openssl s_client -connect yourdomain.com:443
```

### Problem: "Pending updates stuck"

```bash
# Solution: Delete và set lại webhook
curl -X POST https://api.telegram.org/bot<YOUR_TOKEN>/deleteWebhook

# Wait 5 seconds...

# Set webhook lại:
curl -X POST https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook \
  -d url=https://yourdomain.com/webhook \
  -d secret_token=your_secret
```

## Security Best Practices

### 1. **Always use WEBHOOK_SECRET** 🔐
```python
# ✅ GOOD - Verify secret token
token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
if token != settings.WEBHOOK_SECRET:
    return web.Response(status=403)  # Reject
```

### 2. **Use HTTPS only** 🔒
```
❌ DON'T: http://yourdomain.com/webhook
✅ DO: https://yourdomain.com/webhook
```

### 3. **Generate strong secret** 🎲
```bash
# Generate 32-byte random secret
openssl rand -hex 32
# Output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### 4. **Rotate secret periodically** 🔄
```python
# Old: secret_old = "a1b2c3..."
# New: secret_new = "z9y8x7..."

# 1. Update bot to accept both
# 2. Wait 24 hours
# 3. Delete webhook and set with new secret
# 4. Remove old secret from code
```

## Performance Metrics

```
Webhook Mode (Production):
├─ Message latency: 0.2-0.5s
├─ CPU per request: ~5-10ms
├─ Memory: ~50MB base
├─ Throughput: 100+ messages/sec
└─ Cost: ~$20-30/month (Azure)

Long Polling Mode (Development):
├─ Message latency: 25-30s
├─ CPU per request: ~10-20ms (continuous)
├─ Memory: ~80MB base
├─ Throughput: 10-20 messages/sec
└─ Cost: ~$40-60/month (Azure)