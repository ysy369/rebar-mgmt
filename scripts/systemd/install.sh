#!/bin/bash
# ============================================
# 钢筋精细化管理平台 — systemd 单元安装脚本
# ============================================
# 用法（需要 root 权限）：
#   sudo ./scripts/systemd/install.sh
# 作用：
#   1. 复制 .service / .timer 文件到 /etc/systemd/system/
#   2. 重新加载 systemd
#   3. 设置开机自启并立即启动

set -e

PROJECT_DIR="/opt/rebar-mgmt"
UNIT_DIR="/etc/systemd/system"

if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 权限运行：sudo $0"
    exit 1
fi

if [ ! -d "$PROJECT_DIR" ]; then
    echo "项目目录不存在：$PROJECT_DIR"
    echo "请先将项目部署到 /opt/rebar-mgmt 或修改本脚本中的 PROJECT_DIR"
    exit 1
fi

echo "安装 systemd 单元到 $UNIT_DIR ..."
cp "$PROJECT_DIR/scripts/systemd/rebar-mgmt.service" "$UNIT_DIR/"
cp "$PROJECT_DIR/scripts/systemd/rebar-health-watchdog.service" "$UNIT_DIR/"
cp "$PROJECT_DIR/scripts/systemd/rebar-health-watchdog.timer" "$UNIT_DIR/"

echo "重新加载 systemd ..."
systemctl daemon-reload

echo "启用并启动服务 ..."
systemctl enable --now rebar-mgmt.service
systemctl enable --now rebar-health-watchdog.timer

echo "查看 timer 状态："
systemctl status rebar-health-watchdog.timer --no-pager

echo "查看服务状态："
systemctl status rebar-mgmt.service --no-pager

echo "安装完成。平台将在开机时自动启动，看门狗每 30 秒检查一次健康。"
