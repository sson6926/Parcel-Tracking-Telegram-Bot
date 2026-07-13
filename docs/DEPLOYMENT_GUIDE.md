# Deployment Guide - Dual Mode Configuration

## Quick Start

### 1. Development (Long Polling Mode)
```bash
# .env configuration
BOT_MODE=polling
BOT_TOKEN=your_token
DATABASE_URL=...

# Run bot
docker-compose up
```

### 2. Production (Webhook Mode)
```bash
# .env configuration
BOT_MODE=webhook
WEBHOOK_URL=https://yourdomain.com
WEBHOOK_SECRET=your_generated_secret
BOT_TOKEN=your_token
DATABASE_URL=...

# Generate secret
openssl rand -hex 32

# Run bot (exposes port 8443)
docker-compose up -d
```

## Configuration Variables

### Required for both modes:
- `BOT_TOKEN`: Telegram bot token from @BotFather
- `DATABASE_URL`: Database connection string

### Mode-specific:
- `BOT_MODE`: `"polling"` (default) or `"webhook"`
- `WEBHOOK_URL`: Full HTTPS URL (required for webhook mode)
- `WEBHOOK_PATH`: `/webhook` (default)
- `WEBHOOK_PORT`: `8443` (default)
- `WEBHOOK_SECRET`: Secret token for webhook security

## How It Works

### Polling Mode (Development)
```
Bot (polling)
    ↓
Requests updates from Telegram every 30 seconds
    ↓
Processes updates
    ↓
Returns to polling
```

**Pros:**
- No public URL needed
- Works behind NAT/firewall
- Easier for local development

**Cons:**
- Higher latency (25-30 seconds)
- More API calls
- Less efficient

### Webhook Mode (Production)
```
Telegram Server
    ↓
HTTPS POST /webhook
    ↓
Bot verifies secret token
    ↓
Processes update immediately
    ↓
Returns 200 OK
```

**Pros:**
- Real-time updates (< 1 second)
- Less API calls
- More efficient
- Better scalability

**Cons:**
- Requires public HTTPS URL
- Needs SSL certificate
- Port must be accessible

## Docker Deployment

### Build image
```bash
docker build -t parcel-tracking-bot .
```

### Run in polling mode
```bash
docker run -d \
  --env-file .env \
  --name bot \
  parcel-tracking-bot
```

### Run in webhook mode
```bash
# Update .env with webhook configuration
WEBHOOK_URL=https://yourdomain.com
WEBHOOK_PORT=8443

# Run with port mapping
docker run -d \
  -p 8443:8443 \
  --env-file .env \
  --name bot \
  parcel-tracking-bot
```

### Using docker-compose
```yaml
services:
  bot:
    build: .
    env_file:
      - .env
    ports:
      - "${WEBHOOK_PORT:-8443}:${WEBHOOK_PORT:-8443}"
    restart: unless-stopped
```

## Nginx Reverse Proxy

### For Webhook Mode

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /webhook {
        proxy_pass http://localhost:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://localhost:8443;
    }
}
```

## SSL Certificate

### Let's Encrypt (Free)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renew
sudo certbot renew
```

## Monitoring

### Health Check
```bash
curl http://localhost:8443/health
# Expected: "OK"
```

### Webhook Status
```bash
# Check webhook configuration
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo

# Delete webhook (if needed)
curl https://api.telegram.org/bot<TOKEN>/deleteWebhook

# Set webhook manually
curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook \
  -d url=https://yourdomain.com/webhook \
  -d secret_token=your_secret
```

## Troubleshooting

### Bot not receiving updates

1. Check webhook status:
```bash
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

2. Verify SSL:
```bash
openssl s_client -connect yourdomain.com:443
```

3. Check bot logs:
```bash
docker-compose logs -f bot
```

4. Test webhook endpoint:
```bash
curl -X POST https://yourdomain.com/webhook \
  -H "Content-Type: application/json" \
  -d '{"update_id": 1, "message": {"text": "test"}}'
```

### SSL Certificate Error

- Use Let's Encrypt for free SSL
- Ensure certificate is valid and not expired
- Check certificate chain

### Port Not Accessible

- Verify port is open: `nmap -p 8443 yourdomain.com`
- Check firewall rules
- Verify port mapping in docker-compose

## Security Best Practices

1. **Always use WEBHOOK_SECRET**
2. **Use HTTPS only**
3. **Rotate secrets periodically**
4. **Monitor logs regularly**
5. **Set up rate limiting**

## Cost Comparison

| Mode | API Calls | CPU Usage | Bandwidth | Cost |
|------|-----------|-----------|-----------|------|
| Polling | High (continuous) | Medium | High | ~$40-60/mo |
| Webhook | Low (on-demand) | Low | Low | ~$20-30/mo |