#!/bin/bash
set -euo pipefail
GREEN='\033[0;32m'; NC='\033[0m'
log() { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

log "Pulling latest changes..."
git pull origin main

log "Building new image..."
docker compose -f deploy/docker-compose.yml build app

log "Rolling update (zero downtime)..."
docker compose -f deploy/docker-compose.yml up -d --no-deps app

log "Running migrations..."
sleep 3
docker compose -f deploy/docker-compose.yml exec app python3 -c "
import asyncio, sys
sys.path.insert(0, '/app')
from server.models.database import init_db
asyncio.run(init_db())
"

log "Cleaning up old images..."
docker image prune -f

log "Update complete!"
