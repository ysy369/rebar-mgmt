# ============================================
# 钢筋精细化管理平台 — 扩展台账模型
# 翻样/非预算/桩基/基坑支护（待甲方提供Excel模板后补充解析函数）
# ============================================
from datetime import datetime

from app import db


class DetailingRecord(db.Model):
    """钢筋翻样台账"""

    __tablename__ = "detailing_records"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True
    )
    imported_file_id = db.Column(
        db.Integer, db.ForeignKey("imported_files.id"), nullable=True
    )
    date = db.Column(db.Date, index=True, comment="日期（按月筛选）")
    spec = db.Column(db.String(50), comment="规格型号")
    weight_ton = db.Column(db.Numeric(10, 3), comment="重量（吨）")
    remark = db.Column(db.String(200), comment="备注")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project", backref="detailing_records")

    def __repr__(self):
        return f"<DetailingRecord {self.date} spec={self.spec}>"


class NonBudgetRecord(db.Model):
    """非预算收入使用钢筋台账"""

    __tablename__ = "non_budget_records"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True
    )
    imported_file_id = db.Column(
        db.Integer, db.ForeignKey("imported_files.id"), nullable=True
    )
    date = db.Column(db.Date, index=True, comment="日期（按月筛选）")
    spec = db.Column(db.String(50), comment="规格型号")
    weight_ton = db.Column(db.Numeric(10, 3), comment="重量（吨）")
    remark = db.Column(db.String(200), comment="备注")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project", backref="non_budget_records")

    def __repr__(self):
        return f"<NonBudgetRecord {self.date} spec={self.spec}>"


class PileFoundationRecord(db.Model):
    """主体桩基台账"""

    __tablename__ = "pile_foundation_records"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True
    )
    imported_file_id = db.Column(
        db.Integer, db.ForeignKey("imported_files.id"), nullable=True
    )
    date = db.Column(db.Date, index=True, comment="日期（按月筛选）")
    spec = db.Column(db.String(50), comment="规格型号")
    weight_ton = db.Column(db.Numeric(10, 3), comment="重量（吨）")
    remark = db.Column(db.String(200), comment="备注")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project", backref="pile_foundation_records")

    def __repr__(self):
        return f"<PileFoundationRecord {self.date} spec={self.spec}>"


class SupportStructureRecord(db.Model):
    """基坑支护台账"""

    __tablename__ = "support_structure_records"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True
    )
    imported_file_id = db.Column(
        db.Integer, db.ForeignKey("imported_files.id"), nullable=True
    )
    date = db.Column(db.Date, index=True, comment="日期（按月筛选）")
    spec = db.Column(db.String(50), comment="规格型号")
    weight_ton = db.Column(db.Numeric(10, 3), comment="重量（吨）")
    remark = db.Column(db.String(200), comment="备注")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project", backref="support_structure_records")

    def __repr__(self):
        return f"<SupportStructureRecord {self.date} spec={self.spec}>"
