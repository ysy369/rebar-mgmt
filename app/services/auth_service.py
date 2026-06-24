# ============================================
# 钢筋精细化管理平台 — 认证与权限服务
# ============================================
import json
from functools import wraps

from flask import abort, request
from flask_login import current_user

from app import db
from app.models.audit import OperationLog
from app.models.project import Project, UserProject


def admin_required(f):
    """管理员权限装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


def get_user_projects(user_id: int):
    """获取用户被授权的项目列表"""
    return (
        Project.query.join(UserProject)
        .filter(UserProject.user_id == user_id)
        .filter(Project.status == "active")
        .all()
    )


def can_access_project(user_id: int, project_id: int) -> bool:
    """检查用户是否有权访问指定项目"""
    from app.models.user import User

    user = User.query.get(user_id)
    if user and user.is_admin:
        return True
    exists = UserProject.query.filter_by(
        user_id=user_id, project_id=project_id
    ).first()
    return exists is not None


def project_access_required(f):
    """项目访问权限装饰器——确保用户有权访问URL中的项目"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        project_id = kwargs.get("project_id") or kwargs.get("id")
        if project_id and not can_access_project(current_user.id, int(project_id)):
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


def log_operation(user_id: int, action: str, target: str = None, ip: str = None):
    """记录操作日志"""
    try:
        detail = {}
        log_entry = OperationLog(
            user_id=user_id,
            action=action,
            target=target,
            detail=detail,
            ip_address=ip or request.remote_addr,
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
