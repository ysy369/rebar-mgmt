# ============================================
# 钢筋精细化管理平台 — Dockerfile
# ============================================
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（MySQL 客户端库）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建上传和导出目录
RUN mkdir -p uploads exports

# 暴露端口
EXPOSE 5000

# 使用 waitress 作为生产 WSGI 服务器
CMD ["python", "-c", "from waitress import serve; from app import create_app; serve(create_app(), host='0.0.0.0', port=5000)"]
