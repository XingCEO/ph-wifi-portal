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

# Check Ubuntu
if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    warn "This script is tested on Ubuntu 22.04+. Proceeding anyway..."
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

section "Firewall Setup"
if command -v ufw &>/dev/null; then
    ufw allow 80/tcp   # HTTP
    ufw allow 443/tcp  # HTTPS
    ufw allow 29810/udp  # Omada Discovery
    ufw allow 29811/tcp  # Omada AP management
    ufw allow 29812/tcp  # Omada AP adoption
    ufw allow 29813/tcp  # Omada AP upgrade
    ufw allow 29814/tcp  # Omada AP manager v2
    log "Firewall rules added (80, 443, 29810-29814)"
fi

section "Configure Environment"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/server/.env"

if [ -f "$ENV_FILE" ]; then
    warn ".env already exists. Skipping interactive setup."
else
    echo ""
    echo "Please provide the following configuration:"
    echo ""

    read -p "  Domain name (e.g., abotkamay.net): " DOMAIN
    read -s -p "  Admin dashboard password: " ADMIN_PASSWORD; echo
    read -p "  Adcash Zone Key (leave blank if not ready): " ADCASH_ZONE_KEY

    # Generate secrets
    SECRET_KEY=$(openssl rand -hex 32)
    POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '=/+' | head -c 20)

    cat > "$ENV_FILE" << EOF
# AbotKamay WiFi — Environment Configuration
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

# Omada Software Controller (runs in Docker alongside this app)
# ⚠ OMADA_CONTROLLER_ID 需要先啟動 Omada Controller 後才能取得
#   1. 啟動服務後開 https://omada.$DOMAIN 完成初始設定
#   2. 登入後在 URL 找到 controller_id（像 65a8b3c...）
#   3. 建立 Hotspot Manager operator 帳號
#   4. 填入以下三個值後執行: docker compose restart app
OMADA_HOST=omada
OMADA_PORT=8043
OMADA_CONTROLLER_ID=
OMADA_OPERATOR=
OMADA_PASSWORD=

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

    # Save domain for nginx
    echo "$DOMAIN" > "$PROJECT_DIR/deploy/.domain"
fi

section "SSL Certificate"
DOMAIN="${DOMAIN:-$(cat "$PROJECT_DIR/deploy/.domain" 2>/dev/null || echo "")}"
[ -z "$DOMAIN" ] && error "No domain configured. Delete .env and re-run setup."

if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    # Request certificate for main domain + omada subdomain
    docker run -d --name certbot-temp -p 80:80 nginx:alpine
    sleep 2
    docker run --rm --volumes-from certbot-temp \
        -v /etc/letsencrypt:/etc/letsencrypt \
        certbot/certbot certonly --webroot \
        -w /usr/share/nginx/html \
        -d "$DOMAIN" -d "omada.$DOMAIN" \
        --agree-tos --email "admin@$DOMAIN" --non-interactive \
        || warn "SSL setup failed. You can set it up manually later."
    docker stop certbot-temp && docker rm certbot-temp 2>/dev/null || true
    log "SSL certificate obtained for $DOMAIN + omada.$DOMAIN"
else
    log "SSL certificate already exists for $DOMAIN"
fi

section "Prepare Nginx Config"
# Replace $DOMAIN placeholder in nginx.conf
NGINX_CONF="$PROJECT_DIR/deploy/nginx.conf"
if grep -q '\$DOMAIN' "$NGINX_CONF"; then
    sed -i "s/\\\$DOMAIN/$DOMAIN/g" "$NGINX_CONF"
    log "Nginx config updated with domain: $DOMAIN"
fi

section "Start Services"
cd "$PROJECT_DIR"
docker compose -f deploy/docker-compose.yml build
docker compose -f deploy/docker-compose.yml up -d
log "All 8 services started"

section "Database Migration"
sleep 5
docker compose -f deploy/docker-compose.yml exec app python3 -c "
import asyncio, sys
sys.path.insert(0, '/app')
from server.models.database import init_db
asyncio.run(init_db())
print('Database initialized')
"
log "Database initialized"

section "Wait for Omada Controller"
echo -e "  Omada Controller is starting (Java, takes ~60s)..."
for i in $(seq 1 12); do
    if docker compose -f deploy/docker-compose.yml exec omada curl -sf -k https://localhost:8043 > /dev/null 2>&1; then
        log "Omada Controller is ready"
        break
    fi
    sleep 10
done

section "Health Check"
sleep 3
if curl -sf http://localhost/health > /dev/null; then
    log "Health check passed"
else
    warn "Health check failed. Check: docker compose -f deploy/docker-compose.yml logs"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ AbotKamay WiFi Platform is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Brand Website:      ${BLUE}https://$DOMAIN${NC}"
echo -e "  Captive Portal:     ${BLUE}https://$DOMAIN/portal${NC}"
echo -e "  Admin Dashboard:    ${BLUE}https://$DOMAIN/admin/${NC}"
echo -e "  Omada Controller:   ${BLUE}https://omada.$DOMAIN${NC}"
echo -e "  Health Check:       ${BLUE}https://$DOMAIN/health${NC}"
echo ""
echo -e "${YELLOW}  ⚡ 下一步：${NC}"
echo -e "  1. 開瀏覽器 → ${BLUE}https://omada.$DOMAIN${NC}"
echo -e "  2. 完成 Omada Controller 初始設定"
echo -e "  3. 建立 Site → WiFi SSID → External Portal URL:"
echo -e "     ${BLUE}https://$DOMAIN/portal${NC}"
echo -e "  4. 建立 Hotspot Manager operator 帳號"
echo -e "  5. 取得 controller_id（URL 中的長字串）"
echo -e "  6. 編輯 ${BLUE}$ENV_FILE${NC}"
echo -e "     填入 OMADA_CONTROLLER_ID, OMADA_OPERATOR, OMADA_PASSWORD"
echo -e "  7. 重啟 app: ${BLUE}docker compose -f deploy/docker-compose.yml restart app${NC}"
echo -e "  8. 現場 EAP AP 設定 Controller Host → ${BLUE}$(curl -s ifconfig.me)${NC}"
echo ""
