# ============================================
# 钢筋精细化管理平台 — 审计/日志模型
# ============================================
from datetime import datetime

from app import db


class ImportLog(db.Model):
    """导入日志"""

    __tablename__ = "import_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    data_type = db.Column(
        db.String(50),
        nullable=False,
        comment="incoming/transfer/measure_rebar/inventory/waste/model_quantity",
    )
    file_name = db.Column(db.String(255), nullable=False)
    total_rows = db.Column(db.Integer, nullable=False, default=0)
    success_rows = db.Column(db.Integer, nullable=False, default=0)
    error_rows = db.Column(db.Integer, nullable=False, default=0)
    error_detail = db.Column(db.JSON, nullable=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    project = db.relationship("Project")
    creator = db.relationship("User")

    __table_args__ = (db.Index("idx_import_logs_project", "project_id", "created_at"),)

    def __repr__(self):
        return f"<ImportLog {self.data_type} {self.file_name}>"


class OperationLog(db.Model):
    """操作日志"""

    __tablename__ = "operation_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action = db.Column(db.String(100), nullable=False)
    target = db.Column(db.String(200), nullable=True)
    detail = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")

    def __repr__(self):
        return f"<OperationLog {self.action} by user={self.user_id}>"
