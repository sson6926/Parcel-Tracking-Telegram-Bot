# Bot Deployment Modes

This bot supports two deployment modes: **Long Polling** (for development) and **Webhook** (for production).

## Long Polling Mode (Development)

Long polling is recommended for local development as it doesn't require a public URL or SSL certificate.

### Configuration

Set in your `.env` file:
```env
BOT_MODE=polling
```

### How it works
- Bot actively requests updates from Telegram servers
- No public URL needed
- Works behind NAT/firewall
- Easier for local development

### Start the bot
```bash
docker-compose up
```

## Webhook Mode (Production)

Webhook mode is recommended for production as it's more efficient and scalable.

### Prerequisites
1. A public domain with HTTPS (Telegram requires SSL)
2. Domain should point to your server
3. Ports should be open (recommended: 8443, 443, 80, or 88)

### Configuration

Set in your `.env` file:
```env
BOT_MODE=webhook
WEBHOOK_URL=https://yourdomain.com
WEBHOOK_PATH=/webhook
WEBHOOK_PORT=8443
WEBHOOK_SECRET=your_random_secret_here
```

### How it works
- Telegram sends updates directly to your server
- More efficient (no constant polling)
- Requires public HTTPS endpoint
- Better for production scale

### Security
- Always use a `WEBHOOK_SECRET` token in production
- The bot verifies this token on each incoming request
- Generate a strong random secret: `openssl rand -hex 32`

### Nginx Configuration Example

If using nginx as reverse proxy:

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

## Switching Between Modes

### Development to Production
1. Update `.env`:
   ```env
   BOT_MODE=webhook
   WEBHOOK_URL=https://yourdomain.com
   WEBHOOK_SECRET=your_secret_here
   ```

2. Ensure your domain points to the server

3. Restart the bot:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Production to Development
1. Update `.env`:
   ```env
   BOT_MODE=polling
   ```

2. Restart the bot:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Health Check

Both modes expose a health check endpoint at `/health` (webhook mode only):
```bash
curl http://localhost:8443/health
```

## Troubleshooting

### Webhook not receiving updates
1. Check if webhook is set correctly:
   ```bash
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo
   ```

2. Verify SSL certificate is valid
3. Check if port is accessible from internet
4. Review bot logs for errors

### Polling issues
1. Check internet connectivity
2. Verify bot token is correct
3. Ensure no other instance is running in polling mode
4. Check bot logs

## Best Practices

### Development
- Use polling mode
- Test locally without exposing ports
- Use `.env` file (never commit it)

### Production
- Use webhook mode
- Set strong `WEBHOOK_SECRET`
- Use HTTPS with valid certificate
- Monitor logs regularly
- Set up proper logging and monitoring
- Use environment variables for sensitive data
- Consider using container orchestration (Kubernetes, Docker Swarm)

## Azure Deployment

For Azure-specific deployment instructions with webhook mode, see [AZURE_DEPLOYMENT.md](./AZURE_DEPLOYMENT.md).