#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# PH WiFi Portal — 資料備份腳本
# 用法：bash deploy/backup.sh [--s3=s3://bucket/path]
# Cron:  0 2 * * * bash /opt/ph-wifi-system/deploy/backup.sh >> /var/log/ph-wifi-backup.log 2>&1
# ─────────────────────────────────────────────────────────────

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()   { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 設定
BACKUP_DIR="${BACKUP_DIR:-/var/backups/ph-wifi}"
KEEP_BACKUPS=7
DATE_TAG=$(date +"%Y%m%d_%H%M%S")
S3_TARGET=""

# 解析參數
for arg in "$@"; do
    case $arg in
        --s3=*) S3_TARGET="${arg#*=}" ;;
        --s3)   S3_TARGET="${2:-}"; shift ;;
    esac
done

# 確保備份目錄存在
mkdir -p "$BACKUP_DIR"

# ── 載入 .env ──
ENV_FILE="$PROJECT_DIR/server/.env"
if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE"; set +a
else
    warn ".env not found, using defaults"
fi

POSTGRES_USER="${POSTGRES_USER:-ph_wifi_user}"
POSTGRES_DB="${POSTGRES_DB:-ph_wifi}"

# ── 1. PostgreSQL Dump ──
DUMP_FILE="$BACKUP_DIR/pg_${POSTGRES_DB}_${DATE_TAG}.sql.gz"
log "Backing up PostgreSQL: $POSTGRES_DB → $DUMP_FILE"

cd "$PROJECT_DIR"
docker compose -f deploy/docker-compose.yml exec -T postgres \
    pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | \
    gzip -9 > "$DUMP_FILE"

DUMP_SIZE=$(du -sh "$DUMP_FILE" | cut -f1)
log "DB dump complete: $DUMP_SIZE"

# ── 2. 保留最新 N 個，刪除舊備份 ──
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/pg_*.sql.gz 2>/dev/null | wc -l)
log "Total backups: $BACKUP_COUNT (keeping $KEEP_BACKUPS)"

if [ "$BACKUP_COUNT" -gt "$KEEP_BACKUPS" ]; then
    DELETE_COUNT=$((BACKUP_COUNT - KEEP_BACKUPS))
    log "Removing $DELETE_COUNT old backup(s)..."
    ls -1t "$BACKUP_DIR"/pg_*.sql.gz | tail -n "$DELETE_COUNT" | xargs rm -f
fi

# ── 3. 可選：上傳到 S3/R2 ──
if [ -n "$S3_TARGET" ]; then
    if command -v aws &>/dev/null; then
        log "Uploading to S3/R2: $S3_TARGET"
        aws s3 cp "$DUMP_FILE" "${S3_TARGET}/$(basename "$DUMP_FILE")" \
            --storage-class STANDARD_IA && \
            log "Uploaded to $S3_TARGET" || \
            warn "Upload failed — backup stored locally"
    elif command -v rclone &>/dev/null; then
        log "Uploading via rclone: $S3_TARGET"
        rclone copy "$DUMP_FILE" "$S3_TARGET" && \
            log "Uploaded via rclone" || \
            warn "rclone upload failed"
    else
        warn "S3 target set but aws-cli/rclone not installed"
        warn "Install: apt-get install awscli"
    fi
fi

# ── 4. 備份清單 ──
log "Current backups:"
ls -lh "$BACKUP_DIR"/pg_*.sql.gz 2>/dev/null | awk '{print "  "$5, $9}' || echo "  (none)"

echo ""
log "Backup complete: $DUMP_FILE ($DUMP_SIZE)"

# ── 還原說明 ──
# gunzip -c "$DUMP_FILE" | \
#   docker compose -f deploy/docker-compose.yml exec -T postgres \
#   psql -U "$POSTGRES_USER" "$POSTGRES_DB"
