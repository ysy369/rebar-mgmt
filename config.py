import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """基础配置（所有环境共用）"""
    # 密钥：生产环境必须通过环境变量设置
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Login
    REMEMBER_COOKIE_DURATION = timedelta(hours=8)

    # 会话安全
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # SESSION_COOKIE_SECURE = True  # 生产环境启用HTTPS后取消注释

    # 上传与导出
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    EXPORT_FOLDER = os.path.join(basedir, "exports")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Redis / Celery
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # 分页
    PAGE_SIZE = 20


class DevelopmentConfig(Config):
    """开发环境"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://rebar:changeme@127.0.0.1:3306/rebar_mgmt?charset=utf8mb4",
    )


class ProductionConfig(Config):
    """生产环境"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://localhost:3306/rebar_mgmt?charset=utf8mb4",
    )


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
