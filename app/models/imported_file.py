# ============================================
# 钢筋精细化管理平台 — 导入文件模型
# ============================================
from datetime import datetime

from app import db


class ImportedFile(db.Model):
    """项目导入文件表（Excel 上传记录）"""

    __tablename__ = "imported_files"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="项目ID",
    )
    ledger_type = db.Column(
        db.Enum(
            "incoming",
            "transfer",
            "measure_rebar",
            "fangyang_requisition",
            "inventory",
            "waste",
            "progress",
            "model_quantity",
            "secondary",
            "detailing",
            "non_budget",
            "pile_foundation",
            "support_structure",
        ),
        nullable=False,
        comment="台账类型",
    )
    original_filename = db.Column(db.String(255), nullable=False, comment="原始文件名")
    file_path = db.Column(db.String(500), nullable=False, comment="存储路径")
    file_size = db.Column(db.Integer, nullable=True, comment="文件大小(字节)")
    uploaded_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="上传人ID"
    )
    uploaded_at = db.Column(
        db.DateTime, default=datetime.utcnow, comment="上传时间"
    )
    # 异步导入字段
    task_id = db.Column(
        db.String(100), nullable=True, comment="Celery 任务ID"
    )
    status = db.Column(
        db.String(20), nullable=False, default="pending",
        comment="导入状态: pending/processing/completed/failed"
    )
    progress = db.Column(
        db.Integer, nullable=False, default=0, comment="进度 0-100"
    )
    error_message = db.Column(
        db.Text, nullable=True, comment="失败时的错误信息"
    )

    # 关系
    project = db.relationship("Project", back_populates="imported_files")
    uploader = db.relationship("User")

    def __repr__(self):
        return f"<ImportedFile {self.original_filename} ({self.ledger_type})>"
