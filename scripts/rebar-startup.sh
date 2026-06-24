#!/bin/bash
# ============================================
# 钢筋精细化管理平台 — Linux 开机启动脚本
# ============================================
# 用法：由 systemd 服务调用，或手动执行
#   ./scripts/rebar-startup.sh
# 作用：切换到项目根目录并启动/重启 Docker Compose 平台

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/startup.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=========================================="
log "启动/重启 钢筋精细化管理平台"
log "项目目录: $PROJECT_DIR"
log "=========================================="

cd "$PROJECT_DIR"

# 优先使用新版 docker compose 命令
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

log "使用命令: $COMPOSE_CMD"

$COMPOSE_CMD pull
$COMPOSE_CMD up -d --remove-orphans

log "平台已启动，容器状态："
docker ps --filter "name=rebar-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | tee -a "$LOG_FILE"

log "启动脚本执行完毕"
