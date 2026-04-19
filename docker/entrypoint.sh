#!/bin/sh
set -e

echo "Initializing database..."
python -c "from db.database import init_db; init_db()"

echo "Starting bot..."
exec python -m bot.main
