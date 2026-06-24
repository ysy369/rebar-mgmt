# ============================================
# 钢筋精细化管理平台 — 六大核心数据模型 + 汇总分析
# ============================================
from datetime import datetime

from app import db


class Incoming(db.Model):
    """进场量（表1钢筋进场台账 / 表3进场量）"""

    __tablename__ = "incoming"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    date = db.Column(db.Date, nullable=False, comment="进场日期")
    receipt_no = db.Column(db.String(100), nullable=True, comment="收料单号")
    brand = db.Column(db.String(100), nullable=True, comment="品牌")
    product_name = db.Column(db.String(100), nullable=True, comment="品名")
    spec = db.Column(db.String(100), nullable=False, comment="规格")
    material = db.Column(db.String(50), nullable=True, comment="材质")
    rebar_length = db.Column(db.DECIMAL(6, 1), nullable=True, comment="型号(m)")
    piece_count = db.Column(db.Integer, nullable=True, comment="件数")
    theory_weight = db.Column(db.DECIMAL(12, 3), nullable=True, comment="理论重量(T)")
    weigh_weight = db.Column(db.DECIMAL(12, 3), nullable=True, comment="过磅后钢筋重量(T)")
    vehicle_gross = db.Column(db.DECIMAL(12, 3), nullable=True, comment="过磅重量车+钢筋①(T)")
    vehicle_tare = db.Column(db.DECIMAL(12, 3), nullable=True, comment="过磅后车重量②(T)")
    plate_no = db.Column(db.String(20), nullable=True, comment="车牌号")
    use_location = db.Column(db.String(200), nullable=True, comment="使用部位")
    labor_team = db.Column(db.String(200), nullable=True, comment="使用劳务队")
    remark = db.Column(db.Text, nullable=True, comment="备注")
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    project = db.relationship("Project")
    creator = db.relationship("User")

    # 索引
    __table_args__ = (
        db.Index("idx_incoming_project_date", "project_id", "date"),
    )

    def __repr__(self):
        return f"<Incoming {self.date} spec={self.spec} weight={self.weigh_weight}>"


class Transfer(db.Model):
    """调拨量（表6调拨确认单：原材+半成品）"""

    __tablename__ = "transfer"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="调出项目ID",
    )
    date = db.Column(db.Date, nullable=False, comment="调拨日期")
    transfer_type = db.Column(
        db.Enum("raw", "semi"), nullable=False, default="raw", comment="原材/半成品"
    )
    direction = db.Column(
        db.Enum("in", "out"), nullable=False, default="out", comment="调拨方向"
    )
    to_project = db.Column(db.String(200), nullable=True, comment="调入接收项目名称")
    spec = db.Column(db.String(100), nullable=True, comment="规格（原材用）")
    component_name = db.Column(db.String(200), nullable=True, comment="构件名称（半成品用）")
    steel_diameter = db.Column(db.String(50), nullable=True, comment="级别直径（半成品用）")
    rebar_sketch = db.Column(db.String(500), nullable=True, comment="钢筋简图mm或计算式")
    cut_length = db.Column(db.DECIMAL(8, 1), nullable=True, comment="下料mm")
    piece_count = db.Column(db.Integer, nullable=True, comment="根数/件数")
    total_pieces = db.Column(db.Integer, nullable=True, comment="总根数")
    weight = db.Column(db.DECIMAL(12, 3), nullable=False, comment="重量(T或kg)")
    remark = db.Column(db.Text, nullable=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project")
    creator = db.relationship("User")

    __table_args__ = (db.Index("idx_transfer_project_date", "project_id", "date"),)

    def __repr__(self):
        return f"<Transfer {self.date} type={self.transfer_type} dir={self.direction}>"


class MeasureRebar(db.Model):
    """措施筋（表2措施量 / 措施筋台账）"""

    __tablename__ = "measure_rebar"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    date = db.Column(db.Date, nullable=False, comment="日期")
    seq_no = db.Column(db.String(50), nullable=True, comment="编号")
    unit_name = db.Column(db.String(200), nullable=True, comment="使用单位")
    work_type = db.Column(db.String(100), nullable=True, comment="使用工种")
    use_location = db.Column(db.String(200), nullable=True, comment="使用部位")
    usage_purpose = db.Column(db.String(200), nullable=True, comment="用途")
    spec_hrb400 = db.Column(db.String(100), nullable=True, comment="规格型号HRB400")
    spec_hpb300 = db.Column(db.String(100), nullable=True, comment="规格型号HPB300")
    weight_kg = db.Column(db.DECIMAL(12, 3), nullable=False, comment="重量(kg)")
    category = db.Column(
        db.Enum("budget", "non_budget"),
        nullable=False,
        default="non_budget",
        comment="预算内/非预算收入",
    )
    non_budget_type = db.Column(db.String(100), nullable=True, comment="非预算类型")
    signer_name = db.Column(db.String(50), nullable=True, comment="项目签单人")
    signer_title = db.Column(db.String(50), nullable=True, comment="签单人职务")
    labor_leader = db.Column(db.String(50), nullable=True, comment="劳务班组组长")
    remark = db.Column(db.Text, nullable=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project")
    creator = db.relationship("User")

    __table_args__ = (db.Index("idx_measure_rebar_project_date", "project_id", "date"),)

    def __repr__(self):
        return f"<MeasureRebar {self.date} kg={self.weight_kg}>"


class Inventory(db.Model):
    """盘点量/剩余量（表4剩余量 / 钢筋盘点表）"""

    __tablename__ = "inventory"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    inventory_date = db.Column(db.Date, nullable=False, comment="盘点日期")
    category = db.Column(
        db.Enum("raw", "short", "semi", "total"),
        nullable=False,
        comment="原材/短料余头/半成品/合计",
    )
    spec = db.Column(db.String(100), nullable=False, comment="规格")
    piece_count = db.Column(db.Integer, nullable=True, comment="数量(件)")
    unit_weight = db.Column(db.DECIMAL(12, 3), nullable=True, comment="单位重量(吨)")
    total_weight = db.Column(db.DECIMAL(12, 3), nullable=False, comment="合计重量(吨)")
    remark = db.Column(db.Text, nullable=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project")
    creator = db.relationship("User")

    __table_args__ = (
        db.Index("idx_inventory_project_date", "project_id", "inventory_date"),
    )

    def __repr__(self):
        return f"<Inventory {self.inventory_date} cat={self.category} weight={self.total_weight}>"


class Waste(db.Model):
    """废料量（表5废料量 / 废料处理台账）"""

    __tablename__ = "waste"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    process_date = db.Column(db.Date, nullable=False, comment="处理日期")
    receipt_no = db.Column(db.String(100), nullable=True, comment="单号")
    vehicle_before = db.Column(db.DECIMAL(10, 3), nullable=True, comment="过磅前车重量(t)")
    vehicle_after = db.Column(db.DECIMAL(10, 3), nullable=True, comment="过磅后车重量(t)")
    waste_weight = db.Column(db.DECIMAL(12, 3), nullable=False, comment="废料重量(T)")
    rebar_length = db.Column(db.DECIMAL(6, 1), nullable=True, comment="型号(m)")
    labor_team = db.Column(db.String(200), nullable=True, comment="劳务队")
    plate_no = db.Column(db.String(20), nullable=True, comment="车牌号")
    remark = db.Column(db.Text, nullable=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project")
    creator = db.relationship("User")

    __table_args__ = (db.Index("idx_waste_project_date", "project_id", "process_date"),)

    def __repr__(self):
        return f"<Waste {self.process_date} weight={self.waste_weight}>"


class ModelQuantity(db.Model):
    """模型量/主体结构量（表1模型量）"""

    __tablename__ = "model_quantity"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    record_date = db.Column(db.Date, nullable=False, comment="记录日期")
    spec = db.Column(db.String(100), nullable=False, comment="规格")
    structural_weight = db.Column(
        db.DECIMAL(12, 3), nullable=False, comment="主体结构量(T) ①"
    )
    secondary_weight = db.Column(
        db.DECIMAL(12, 3), nullable=True, comment="二构量(T) ④"
    )
    remark = db.Column(db.Text, nullable=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project")
    creator = db.relationship("User")

    __table_args__ = (
        db.Index("idx_model_qty_project_date", "project_id", "record_date"),
    )

    def __repr__(self):
        return f"<ModelQuantity {self.record_date} spec={self.spec}>"


class ProjectAnalysis(db.Model):
    """项目分析汇总（存储 ①~⑬ 计算结果）"""

    __tablename__ = "project_analysis"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="按项目唯一",
    )
    period_start = db.Column(db.Date, nullable=True, comment="统计周期开始")
    period_end = db.Column(db.Date, nullable=True, comment="统计周期结束")

    # 收入维度（对齐大美项目真实公式）
    contract_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="①对甲结算量(T)")
    struct_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="模型量(T)")
    measure_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="措施筋量(T)")
    non_entity_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="非实体量(T)")
    sec_struct_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="二构量(T)")
    budget_qty = db.Column(
        db.DECIMAL(14, 3), default=0, comment="施工图预算量(T)"
    )

    # 使用维度
    incoming_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="进场量(T)")
    remaining_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="剩余量(T)")
    waste_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="废料量(T)")
    const_sec_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="已施工二构量(T)")
    transfer_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="调拨量(T)")
    non_budget_use_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="非预算收入使用量(T)")
    temp_facility_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="临建设施使用量(T)")
    usage_qty = db.Column(
        db.DECIMAL(14, 3), default=0, comment="使用量=进场-剩余-废料-二构-调拨-非预算-临建(T)"
    )

    # 结果
    saved_qty = db.Column(db.DECIMAL(14, 3), default=0, comment="节约量=对甲结算-使用量(T)")
    balance_rate = db.Column(db.DECIMAL(8, 2), nullable=True, comment="结余率=节约/对甲结算*100(%)")

    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 关系
    project = db.relationship("Project", back_populates="analysis")

    def __repr__(self):
        return f"<ProjectAnalysis project={self.project_id} rate={self.balance_rate}%>"
