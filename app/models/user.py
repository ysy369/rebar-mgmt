# ============================================
# 钢筋精细化管理平台 — 用户模型
# ============================================
from datetime import datetime

import bcrypt
from flask_login import UserMixin

from app import db, login_manager


class User(UserMixin, db.Model):
    """用户表"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.Enum("admin", "user"), nullable=False, default="user")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_login_at = db.Column(db.DateTime, nullable=True)

    # 关系
    user_projects = db.relationship("UserProject", back_populates="user", lazy="dynamic")

    # Flask-Login 属性
    @property
    def is_admin(self):
        return self.role == "admin"

    def set_password(self, password: str):
        """使用 bcrypt 设置密码"""
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login 用户加载回调"""
    return User.query.get(int(user_id))
