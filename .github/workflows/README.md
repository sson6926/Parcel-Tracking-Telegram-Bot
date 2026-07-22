# CI/CD Deployment Setup

This workflow automatically builds and deploys the Telegram bot when changes are pushed to the `main` branch.

## Workflow Overview

1. **Build and Push** - Builds Docker image and pushes to GitHub Container Registry
2. **Deploy** - Connects to server via SSH and deploys the new image

## Required GitHub Secrets

You need to set up the following secrets in your GitHub repository:

### Repository Secrets (Settings → Secrets and variables → Actions → New repository secret):

1. **SERVER_HOST** - IP address or domain of your server
2. **SERVER_USER** - SSH username (e.g., `ubuntu`, `root`)
3. **SERVER_SSH_KEY** - Private SSH key for authentication
4. **SERVER_PORT** - SSH port (optional, default: `22`)
5. **PROJECT_PATH** - Path to project on server (e.g., `/home/user/Parcel-Tracking-Telegram-Bot`)

## Server Setup Requirements

### 1. Install Docker and Docker Compose on Server
```bash
# For Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
```

### 2. Clone Repository on Server
```bash
git clone <your-repo-url> <project-path>
cd <project-path>
```

### 3. Create `.env` File on Server
Create the `.env` file in the project directory with your configuration:
```bash
cp .env.example .env
# Edit .env with your actual values
nano .env
```

### 4. Create Docker Network (if needed)
```bash
docker network create tracking-network
```

### 5. Grant GitHub Actions SSH Access
Add your GitHub Actions public key to server's `~/.ssh/authorized_keys`:
```bash
# On server
mkdir -p ~/.ssh
echo "your-public-key-here" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

## How the Deployment Works

1. **When code is pushed to `main` branch:**
   - GitHub Actions triggers the workflow
   - Builds Docker image with multi-platform support
   - Pushes image to GitHub Container Registry

2. **SSH Deployment:**
   - Connects to your server via SSH
   - Navigates to project directory
   - Pulls latest code and Docker image
   - Stops old container
   - Starts new container with updated image

## Troubleshooting

### SSH Connection Issues
- Verify SSH key permissions (should be 600)
- Check firewall settings on server
- Ensure GitHub Actions IP is allowed

### Docker Permission Issues
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Image Pull Issues
- Ensure GitHub Container Registry access token has proper permissions
- Check if `GITHUB_TOKEN` has `packages:write` permission

## Manual Deployment (Fallback)

If GitHub Actions fails, you can manually deploy:
```bash
# On server
cd <project-path>
git pull origin main
docker compose down
docker compose pull
docker compose up -d
```

## Monitoring

Check container status:
```bash
docker ps
docker logs tracking-bot --tail 100
docker compose logs -f
```

## Rollback

If deployment fails, rollback to previous version:
```bash
# On server
cd <project-path>
git checkout <previous-commit>
docker compose down
docker compose up -d