# Deploy to Azure Container Apps

## Prerequisites

1. **Azure Account** với subscription active
2. **Azure CLI** installed: https://learn.microsoft.com/cli/azure/install-azure-cli
3. **Docker image** đã build và push lên GHCR

## Architecture

```
┌─────────────────────────────────────┐
│   Azure Container Apps              │
│   ┌─────────────────────────────┐   │
│   │  Telegram Bot Container     │   │
│   │  - Polling mode             │   │
│   │  - Background scheduler     │   │
│   └─────────────────────────────┘   │
│              ↓                       │
│   ┌─────────────────────────────┐   │
│   │  Azure Database for MySQL   │   │
│   │  - Managed service          │   │
│   │  - Auto backup              │   │
│   └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

## Step 1: Setup Azure Resources

### 1.1 Login to Azure
```bash
az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

### 1.2 Create Resource Group
```bash
RESOURCE_GROUP="rg-telegram-bot"
LOCATION="southeastasia"  # Hoặc "eastasia" cho Hong Kong

az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### 1.3 Create Azure Database for MySQL (Optional)
```bash
# Flexible Server (recommended)
DB_SERVER_NAME="mysql-telegram-bot-$(date +%s)"
DB_ADMIN_USER="botadmin"
DB_ADMIN_PASSWORD="YourSecurePassword123!"  # Change this!
DB_NAME="tracking_db"

az mysql flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --location $LOCATION \
  --admin-user $DB_ADMIN_USER \
  --admin-password $DB_ADMIN_PASSWORD \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 8.0.21

# Create database
az mysql flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER_NAME \
  --database-name $DB_NAME

# Allow Azure services
az mysql flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Get connection string
echo "DATABASE_URL=mysql+pymysql://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${DB_SERVER_NAME}.mysql.database.azure.com:3306/${DB_NAME}?ssl_ca=/etc/ssl/certs/ca-certificates.crt"
```

### 1.4 Create Container Apps Environment
```bash
ENVIRONMENT_NAME="env-telegram-bot"

az containerapp env create \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
```

## Step 2: Deploy Container App

### 2.1 Create Container App
```bash
APP_NAME="telegram-tracking-bot"
IMAGE="ghcr.io/sson6926/parcel-tracking-telegram-bot:latest"

az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image $IMAGE \
  --target-port 8080 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --env-vars \
    "BOT_TOKEN=secretref:bot-token" \
    "DATABASE_URL=secretref:database-url" \
    "CHECK_INTERVAL_MINUTES=5" \
    "LOG_LEVEL=INFO"
```

**Note:** Ingress không cần thiết cho polling bot, nhưng Azure Container Apps yêu cầu.

### 2.2 Set Secrets
```bash
# Bot token
az containerapp secret set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --secrets \
    bot-token="YOUR_TELEGRAM_BOT_TOKEN" \
    database-url="mysql+pymysql://user:pass@host:3306/db"
```

### 2.3 Update Environment Variables
```bash
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    "BOT_TOKEN=secretref:bot-token" \
    "DATABASE_URL=secretref:database-url" \
    "CHECK_INTERVAL_MINUTES=5" \
    "LOG_LEVEL=INFO"
```

## Step 3: Verify Deployment

### 3.1 Check Status
```bash
az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.provisioningState"
```

### 3.2 View Logs
```bash
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow
```

### 3.3 Check Replicas
```bash
az containerapp replica list \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP
```

## Step 4: Update Deployment

### 4.1 Update to New Image
```bash
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image ghcr.io/sson6926/parcel-tracking-telegram-bot:v1.0.0
```

### 4.2 Scale Manually
```bash
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 1 \
  --max-replicas 1
```

## Alternative: Use SQLite with Azure Files

### 1. Create Storage Account
```bash
STORAGE_ACCOUNT="sttelegrambot$(date +%s)"

az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS

# Create file share
az storage share create \
  --name bot-data \
  --account-name $STORAGE_ACCOUNT
```

### 2. Mount Storage in Container App
```bash
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --azure-file-volume-share-name bot-data \
  --azure-file-volume-account-name $STORAGE_ACCOUNT \
  --azure-file-volume-account-key "$(az storage account keys list -g $RESOURCE_GROUP -n $STORAGE_ACCOUNT --query '[0].value' -o tsv)" \
  --azure-file-volume-mount-path /app/data

# Update DATABASE_URL
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars "DATABASE_URL=sqlite:////app/data/tracking.db"
```

## Monitoring

### View Metrics
```bash
# CPU usage
az monitor metrics list \
  --resource "/subscriptions/YOUR_SUB/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$APP_NAME" \
  --metric "UsageNanoCores"

# Memory usage
az monitor metrics list \
  --resource "/subscriptions/YOUR_SUB/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$APP_NAME" \
  --metric "WorkingSetBytes"
```

### Set up Alerts
```bash
# Alert on container restart
az monitor metrics alert create \
  --name "bot-restart-alert" \
  --resource-group $RESOURCE_GROUP \
  --scopes "/subscriptions/YOUR_SUB/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$APP_NAME" \
  --condition "count Restarts > 5" \
  --window-size 5m \
  --evaluation-frequency 1m
```

## Cost Optimization

### Pricing (Southeast Asia)
- **Container Apps**: ~$0.000012/vCPU-second + $0.000002/GiB-second
- **Azure Database for MySQL (Burstable B1ms)**: ~$12/month
- **Storage (if using Azure Files)**: ~$0.05/GB/month

### Estimated Monthly Cost
- Container (0.5 vCPU, 1GB RAM, 24/7): ~$20
- MySQL Flexible Server (B1ms): ~$12
- **Total: ~$32/month**

### Cost Saving Tips
1. Use **SQLite with Azure Files** (~$5/month) thay vì MySQL
2. Stop container khi không dùng (dev/test)
3. Use **Consumption plan** thay vì Dedicated

## Troubleshooting

### Bot không phản hồi
```bash
# Check logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --tail 100

# Restart container
az containerapp revision restart \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP
```

### Database connection error
```bash
# Test connection from container
az containerapp exec \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --command "/bin/bash"

# Inside container
python -c "from app.database import create_session_factory; print('OK')"
```

### High memory usage
```bash
# Increase memory
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --memory 2.0Gi
```

## Cleanup

```bash
# Delete everything
az group delete \
  --name $RESOURCE_GROUP \
  --yes --no-wait
```

## CI/CD with GitHub Actions

See `.github/workflows/azure-deploy.yml` for automated deployment.

## References

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Azure Database for MySQL](https://learn.microsoft.com/azure/mysql/)
- [Azure CLI Reference](https://learn.microsoft.com/cli/azure/)
