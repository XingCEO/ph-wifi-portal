#!/bin/bash
set -euo pipefail

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()     { echo -e "${GREEN}[$(date +%H:%M:%S)] ✓${NC} $1"; }
warn()    { echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠${NC} $1"; }
error()   { echo -e "${RED}[$(date +%H:%M:%S)] ✗ ERROR:${NC} $1"; exit 1; }
section() { echo -e "\n${BLUE}━━━ $1 ━━━${NC}"; }

# Check root
[ "$EUID" -ne 0 ] && error "Run as root: sudo bash setup.sh"

# Check Ubuntu 22.04
if ! grep -q "Ubuntu 22.04" /etc/os-release 2>/dev/null; then
    warn "This script is tested on Ubuntu 22.04. Proceeding anyway..."
fi

section "System Update"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq
log "System updated"

section "Install Docker"
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker "$SUDO_USER" 2>/dev/null || true
    log "Docker installed"
else
    log "Docker already installed: $(docker --version)"
fi

if ! docker compose version &>/dev/null; then
    apt-get install -y -qq docker-compose-plugin
    log "Docker Compose installed"
fi

section "Configure Environment"

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/server/.env"

if [ -f "$ENV_FILE" ]; then
    warn ".env already exists. Skipping interactive setup."
else
    echo ""
    echo "Please provide the following configuration:"
    echo ""

    read -p "  Domain name (e.g., portal.example.com): " DOMAIN
    read -p "  OC200 IP address (e.g., 192.168.1.100): " OMADA_HOST
    read -p "  OC200 Controller ID: " OMADA_CONTROLLER_ID
    read -p "  OC200 Hotspot Operator username: " OMADA_OPERATOR
    read -s -p "  OC200 Hotspot Operator password: " OMADA_PASSWORD; echo
    read -p "  Adcash Zone Key (leave blank if not ready): " ADCASH_ZONE_KEY
    read -s -p "  Admin dashboard password: " ADMIN_PASSWORD; echo

    # Generate secrets
    SECRET_KEY=$(openssl rand -hex 32)
    POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '=/+' | head -c 20)

    cat > "$ENV_FILE" << EOF
# PH WiFi Portal — Environment Configuration
# Generated: $(date)

# Application
ENVIRONMENT=production
SECRET_KEY=$SECRET_KEY

# Database
DATABASE_URL=postgresql+asyncpg://wifi_admin:${POSTGRES_PASSWORD}@postgres:5432/ph_wifi
POSTGRES_USER=wifi_admin
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Redis
REDIS_URL=redis://redis:6379/0

# Omada OC200
OMADA_HOST=$OMADA_HOST
OMADA_PORT=8043
OMADA_CONTROLLER_ID=$OMADA_CONTROLLER_ID
OMADA_OPERATOR=$OMADA_OPERATOR
OMADA_PASSWORD=$OMADA_PASSWORD

# Adcash
ADCASH_ZONE_KEY=$ADCASH_ZONE_KEY

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$ADMIN_PASSWORD

# Business Rules
AD_DURATION_SECONDS=30
SESSION_DURATION_SECONDS=3600
ANTI_SPAM_WINDOW_SECONDS=3600
EOF
    chmod 600 "$ENV_FILE"
    log ".env created at $ENV_FILE"
fi

section "SSL Certificate"
source "$ENV_FILE" 2>/dev/null || true
DOMAIN="${DOMAIN:-your-domain.com}"

if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    # Temp HTTP server for ACME challenge
    docker run -d --name certbot-temp -p 80:80 nginx:alpine
    sleep 2
    docker run --rm --volumes-from certbot-temp \
        -v /etc/letsencrypt:/etc/letsencrypt \
        certbot/certbot certonly --webroot \
        -w /usr/share/nginx/html \
        -d "$DOMAIN" \
        --agree-tos --email "admin@$DOMAIN" --non-interactive || warn "SSL setup failed. You can set it up manually later."
    docker stop certbot-temp && docker rm certbot-temp 2>/dev/null || true
    log "SSL certificate obtained for $DOMAIN"
else
    log "SSL certificate already exists for $DOMAIN"
fi

section "Start Services"
cd "$PROJECT_DIR"
docker compose -f deploy/docker-compose.yml pull
docker compose -f deploy/docker-compose.yml build
docker compose -f deploy/docker-compose.yml up -d
log "Services started"

section "Database Migration"
sleep 5  # Wait for postgres to be ready
docker compose -f deploy/docker-compose.yml exec app python3 -c "
import asyncio, sys
sys.path.insert(0, '/app')
from server.models.database import init_db
asyncio.run(init_db())
print('Database initialized')
"
log "Database initialized"

section "Health Check"
sleep 3
if curl -sf http://localhost/health > /dev/null; then
    log "Health check passed"
else
    error "Health check failed. Check: docker compose -f deploy/docker-compose.yml logs"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ PH WiFi Portal is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Portal URL:   ${BLUE}https://$DOMAIN/portal${NC}"
echo -e "  Admin Panel:  ${BLUE}https://$DOMAIN/admin/${NC}"
echo -e "  Health:       ${BLUE}https://$DOMAIN/health${NC}"
echo ""
echo -e "  OC200 External Portal URL:"
echo -e "  ${YELLOW}https://$DOMAIN/portal${NC}"
echo ""
