# ============================================
# 钢筋精细化管理平台 — 业务扩展模型
# ============================================
from datetime import datetime

from app import db


class Contractor(db.Model):
    """承接公司"""

    __tablename__ = "contractors"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), unique=True, nullable=False, comment="承接公司名称")
    contact_person = db.Column(db.String(100), nullable=True, comment="联系人")
    contact_phone = db.Column(db.String(50), nullable=True, comment="联系电话")
    address = db.Column(db.String(500), nullable=True, comment="地址")
    remark = db.Column(db.Text, nullable=True, comment="备注")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    projects = db.relationship("Project", back_populates="contractor", lazy="dynamic")

    def __repr__(self):
        return f"<Contractor {self.name}>"


class ProjectAttachment(db.Model):
    """项目附件/效果图"""

    __tablename__ = "project_attachments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    attachment_type = db.Column(
        db.Enum("rendering", "document", "other"),
        nullable=False,
        default="rendering",
        comment="附件类型",
    )
    file_name = db.Column(db.String(255), nullable=False, comment="原始文件名")
    file_path = db.Column(db.String(500), nullable=False, comment="服务器存储路径")
    file_size = db.Column(db.Integer, nullable=True, comment="文件大小(bytes)")
    mime_type = db.Column(db.String(100), nullable=True, comment="MIME类型")
    description = db.Column(db.String(500), nullable=True, comment="描述/说明")
    sort_order = db.Column(db.Integer, default=0, comment="排序")
    is_cover = db.Column(db.Boolean, default=False, comment="是否为封面图")
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project")
    creator = db.relationship("User")

    __table_args__ = (db.Index("idx_pa_project", "project_id"),)

    def __repr__(self):
        return f"<ProjectAttachment {self.id} {self.file_name}>"


class CuttingOrder(db.Model):
    """料单审核台账（主表）"""

    __tablename__ = "cutting_orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    order_no = db.Column(db.String(100), nullable=False, comment="料单单号")
    order_date = db.Column(db.Date, nullable=False, comment="料单日期")
    batch_no = db.Column(db.String(100), nullable=True, comment="批次号")
    labor_team = db.Column(db.String(200), nullable=True, comment="劳务队")
    use_location = db.Column(db.String(500), nullable=True, comment="使用部位")
    total_pieces = db.Column(db.Integer, nullable=True, comment="总根数")
    total_weight = db.Column(db.DECIMAL(12, 3), nullable=True, comment="总重量(T)")
    status = db.Column(
        db.Enum("draft", "submitted", "reviewed", "approved", "rejected"),
        nullable=False,
        default="draft",
        comment="审核状态",
    )
    submitted_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at = db.Column(db.DateTime, nullable=True, comment="提交时间")
    reviewed_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at = db.Column(db.DateTime, nullable=True, comment="审核时间")
    review_comment = db.Column(db.Text, nullable=True, comment="审核意见")
    remark = db.Column(db.Text, nullable=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 关系
    project = db.relationship("Project")
    submitter = db.relationship("User", foreign_keys=[submitted_by])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])
    creator = db.relationship("User", foreign_keys=[created_by])
    items = db.relationship(
        "CuttingOrderItem",
        back_populates="order",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.Index("idx_co_project_status", "project_id", "status"),
        db.Index("idx_co_order_date", "order_date"),
    )

    def __repr__(self):
        return f"<CuttingOrder {self.order_no} status={self.status}>"


class CuttingOrderItem(db.Model):
    """料单明细（子表）"""

    __tablename__ = "cutting_order_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey("cutting_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_no = db.Column(db.Integer, nullable=False, comment="行号/序号")
    spec = db.Column(db.String(100), nullable=False, comment="规格")
    rebar_diameter = db.Column(db.String(50), nullable=True, comment="级别直径")
    cut_length = db.Column(db.DECIMAL(8, 1), nullable=True, comment="下料长度(mm)")
    piece_count = db.Column(db.Integer, nullable=True, comment="根数")
    unit_weight = db.Column(db.DECIMAL(12, 3), nullable=True, comment="单根理论重量(kg)")
    total_weight = db.Column(db.DECIMAL(12, 3), nullable=True, comment="总重(kg)")
    rebar_shape = db.Column(db.String(500), nullable=True, comment="钢筋简图描述")
    component_name = db.Column(db.String(200), nullable=True, comment="构件名称")
    remark = db.Column(db.Text, nullable=True)

    order = db.relationship("CuttingOrder", back_populates="items")

    __table_args__ = (db.Index("idx_coi_order", "order_id"),)

    def __repr__(self):
        return f"<CuttingOrderItem {self.id} line={self.line_no}>"


class ProjectCost(db.Model):
    """项目成本"""

    __tablename__ = "project_costs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    cost_date = db.Column(db.Date, nullable=False, comment="费用日期")
    cost_category = db.Column(
        db.Enum("labor", "material", "equipment", "transport", "management", "other"),
        nullable=False,
        comment="费用类别",
    )
    cost_item = db.Column(db.String(200), nullable=False, comment="费用项目名称")
    amount = db.Column(db.DECIMAL(14, 2), nullable=False, comment="金额(元)")
    description = db.Column(db.Text, nullable=True, comment="费用说明")
    receipt_no = db.Column(db.String(100), nullable=True, comment="凭证号")
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    project = db.relationship("Project")
    creator = db.relationship("User")

    __table_args__ = (
        db.Index("idx_pc_project_date", "project_id", "cost_date"),
        db.Index("idx_pc_category", "cost_category"),
    )

    def __repr__(self):
        return f"<ProjectCost {self.id} {self.cost_item} {self.amount}>"


class ProjectProfitLoss(db.Model):
    """项目盈亏分析（缓存表）"""

    __tablename__ = "project_profit_loss"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    rebar_unit_price = db.Column(
        db.DECIMAL(10, 2), nullable=False, default=5000, comment="钢筋节约定价(元/T)"
    )
    rebar_saved_qty = db.Column(
        db.DECIMAL(14, 3), default=0, comment="钢筋节约量(T)"
    )
    rebar_income = db.Column(
        db.DECIMAL(14, 2), default=0, comment="节超收益=节约量×定价"
    )
    other_income = db.Column(db.DECIMAL(14, 2), default=0, comment="其他收入")
    total_income = db.Column(
        db.DECIMAL(14, 2), default=0, comment="总收入=节超收益+其他收入"
    )
    total_cost = db.Column(db.DECIMAL(14, 2), default=0, comment="总成本=SUM(project_costs)")
    net_profit = db.Column(
        db.DECIMAL(14, 2), default=0, comment="净利润=总收入-总成本"
    )
    profit_rate = db.Column(
        db.DECIMAL(8, 2), nullable=True, comment="利润率(%)=净利润/总收入*100"
    )
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    project = db.relationship("Project")

    def __repr__(self):
        return f"<ProjectProfitLoss project={self.project_id} profit={self.net_profit}>"
