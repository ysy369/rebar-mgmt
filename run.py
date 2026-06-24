#!/usr/bin/env python
# ============================================
# 钢筋精细化管理平台 — 开发启动入口
# ============================================
"""开发模式启动。生产环境请使用 Docker 或 waitress 直接启动。"""
import os

# 默认使用开发配置，可通过环境变量 FLASK_ENV=production 切换
os.environ.setdefault("FLASK_ENV", "development")

from app import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 50)
    print(" 钢筋精细化管理平台")
    print(f" 环境: {os.environ.get('FLASK_ENV', 'development')}")
    print(" 访问: http://127.0.0.1:5000")
    print(" 默认账号: admin / admin123")
    print("=" * 50)
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
