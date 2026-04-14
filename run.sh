#!/usr/bin/env bash

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Check if requirements are installed
echo -e "${YELLOW}Checking dependencies...${NC}"
if ! pip install -q -r requirements.txt; then
    echo -e "${RED}❌ Failed to install dependencies${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${RED}❌ Please edit .env and add your BOT_TOKEN${NC}"
    exit 1
fi

# Check BOT_TOKEN
if ! grep -q "BOT_TOKEN=" .env || grep "BOT_TOKEN=your_telegram_bot_token_here" .env > /dev/null; then
    echo -e "${RED}❌ BOT_TOKEN not configured in .env${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All checks passed${NC}"
echo -e "${YELLOW}Starting bot...${NC}"

# Run bot
python3 -m bot.main
