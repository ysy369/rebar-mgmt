"""形象进度模型"""
from datetime import datetime
from app import db


class BuildingProgress(db.Model):
    __tablename__ = "building_progress"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    building_name = db.Column(db.String(200), nullable=False, comment="楼栋名称")
    floor_name = db.Column(db.String(100), nullable=True, comment="楼层")
    component_type = db.Column(db.String(100), nullable=True, comment="构件类型")
    progress_status = db.Column(db.Enum("未施工", "施工中", "已完成"), default="未施工")
    model_total = db.Column(db.DECIMAL(14, 3), default=0, comment="模型总量(kg)")
    progress_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="进度量(kg)")
    total_weight = db.Column(db.DECIMAL(14, 3), default=0, comment="钢筋总重(kg)")
    record_date = db.Column(db.Date, nullable=True)
    remark = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project")
    __table_args__ = (db.Index("idx_bp_project", "project_id"), db.Index("idx_bp_building", "building_name"))
