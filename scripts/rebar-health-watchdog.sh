#!/bin/bash
# ============================================
# 钢筋精细化管理平台 — Linux 健康看门狗脚本
# ============================================
# 作用：
#   1. 调用 http://localhost:5000/health 检查应用健康；
#   2. 通过 docker inspect 获取 rebar-app / rebar-db 容器健康状态；
#   3. 将结果写入 status/rebar-health.json；
#   4. 当检测到不健康时，在 status/rebar-unhealthy.marker 做标记并记录日志；
#   5. 若设置 RESTART_UNHEALTHY=1，看门狗会主动重启不健康的 rebar-app。
# 用法：
#   ./scripts/rebar-health-watchdog.sh
# 推荐配合 systemd timer 每 30 秒执行一次。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
STATUS_DIR="$PROJECT_DIR/status"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$STATUS_DIR" "$LOG_DIR"

STATUS_FILE="$STATUS_DIR/rebar-health.json"
MARKER_FILE="$STATUS_DIR/rebar-unhealthy.marker"
LOG_FILE="$LOG_DIR/health-watchdog.log"
HEALTH_URL="${HEALTH_URL:-http://localhost:5000/health}"
RESTART_UNHEALTHY="${RESTART_UNHEALTHY:-0}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# 获取容器 Health.Status，为空则返回 unknown
container_health() {
    local name="$1"
    local status
    status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || true)
    if [ -z "$status" ]; then
        status="unknown"
    fi
    echo "$status"
}

# 调用 /health
http_status=0
health_body="{}"
tmp_body=$(mktemp)
http_status=$(curl -sS -o "$tmp_body" -w "%{http_code}" --max-time 5 "$HEALTH_URL" 2>/dev/null || echo 0)
health_body=$(cat "$tmp_body" 2>/dev/null || echo "{}")
rm -f "$tmp_body"

app_health="unhealthy"
if [ "$http_status" = "200" ]; then
    app_health="healthy"
fi

app_container_status=$(container_health rebar-app)
db_container_status=$(container_health rebar-db)

overall="healthy"
if [ "$app_health" != "healthy" ] || [ "$app_container_status" != "healthy" ] || [ "$db_container_status" != "healthy" ]; then
    overall="unhealthy"
fi

timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")

# 写入状态文件（先写临时文件再原子替换）
tmp_status=$(mktemp)
cat > "$tmp_status" <<EOF
{
  "timestamp": "$timestamp",
  "app": {
    "http_status": $http_status,
    "health": "$app_health",
    "detail": $health_body
  },
  "containers": {
    "rebar-app": "$app_container_status",
    "rebar-db": "$db_container_status"
  },
  "overall": "$overall"
}
EOF
mv "$tmp_status" "$STATUS_FILE"

if [ "$overall" = "unhealthy" ]; then
    touch "$MARKER_FILE"
    log "WARNING: 平台不健康 | app=$app_health($http_status) | rebar-app=$app_container_status | rebar-db=$db_container_status"

    if [ "$RESTART_UNHEALTHY" = "1" ] && [ "$app_container_status" != "healthy" ]; then
        log "INFO: RESTART_UNHEALTHY=1，尝试重启 rebar-app ..."
        if docker restart rebar-app >&1; then
            log "INFO: rebar-app 重启命令已下发"
        else
            log "ERROR: rebar-app 重启失败"
        fi
    fi
else
    if [ -f "$MARKER_FILE" ]; then
        rm -f "$MARKER_FILE"
        log "INFO: 平台恢复健康，移除不健康标记"
    fi
fi
