# ============================================
# 钢筋精细化管理平台 — Celery 异步任务初始化
# ============================================
import os
from celery import Celery
from celery.signals import worker_process_init

# 模块级 Celery 实例（celery -A app.celery_app worker 命令需要）
celery = Celery(
    "app",
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    include=["app.services.ledger_import"],
)
celery.conf.update(
    result_expires=3600,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=300,
)


def _setup_context_task(app):
    """用给定的 Flask app 替换 Celery Task 类（注入应用上下文）"""

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask


@worker_process_init.connect
def _init_worker_context(**kwargs):
    """Worker 进程启动时：创建 Flask 应用并注入 Celery Task 上下文"""
    from app import create_app
    app = create_app()
    _setup_context_task(app)
    celery.conf.update(
        broker_url=app.config.get("REDIS_URL", "redis://localhost:6379/0"),
        result_backend=app.config.get("REDIS_URL", "redis://localhost:6379/0"),
    )


def make_celery(app):
    """Web 进程调用：注入当前 Flask 应用上下文到 Celery"""
    celery.conf.update(
        broker_url=app.config.get("REDIS_URL", "redis://localhost:6379/0"),
        result_backend=app.config.get("REDIS_URL", "redis://localhost:6379/0"),
    )
    _setup_context_task(app)
    return celery
