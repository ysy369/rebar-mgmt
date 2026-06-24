# ============================================
# 钢筋精细化管理平台 — 配料单(BOM)数据模型
# ============================================
from datetime import datetime

from app import db


class Building(db.Model):
    """楼栋"""

    __tablename__ = "buildings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(200), nullable=False, comment="楼栋名称")

    project = db.relationship("Project")
    floors = db.relationship("Floor", back_populates="building", lazy="dynamic",
                             cascade="all, delete-orphan")

    __table_args__ = (db.Index("idx_building_project", "project_id"),)

    def __repr__(self):
        return f"<Building {self.name}>"


class Floor(db.Model):
    """楼层"""

    __tablename__ = "floors"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    building_id = db.Column(
        db.Integer, db.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(100), nullable=False, comment="楼层名称")
    sort_order = db.Column(db.Integer, default=0, comment="排序")

    building = db.relationship("Building", back_populates="floors")
    areas = db.relationship("Area", back_populates="floor", lazy="dynamic",
                            cascade="all, delete-orphan")

    __table_args__ = (db.Index("idx_floor_building", "building_id"),)

    def __repr__(self):
        return f"<Floor {self.name}>"


class Area(db.Model):
    """区域"""

    __tablename__ = "areas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    floor_id = db.Column(
        db.Integer, db.ForeignKey("floors.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(100), nullable=False, comment="区域名称")

    floor = db.relationship("Floor", back_populates="areas")
    components = db.relationship("Component", back_populates="area", lazy="dynamic",
                                 cascade="all, delete-orphan")

    __table_args__ = (db.Index("idx_area_floor", "floor_id"),)

    def __repr__(self):
        return f"<Area {self.name}>"


class Component(db.Model):
    """构件"""

    __tablename__ = "components"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    area_id = db.Column(
        db.Integer, db.ForeignKey("areas.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(200), nullable=False, comment="构件名称")
    component_type = db.Column(
        db.Enum("column", "beam", "slab", "wall", "stair", "other"),
        nullable=False,
        default="other",
        comment="构件类型",
    )
    status = db.Column(
        db.Enum("not_started", "in_progress", "poured"),
        nullable=False,
        default="not_started",
        comment="施工状态",
    )

    area = db.relationship("Area", back_populates="components")
    rebar_details = db.relationship("RebarDetail", back_populates="component",
                                    lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (db.Index("idx_component_area", "area_id"),
                      db.Index("idx_component_status", "status"))

    @property
    def total_weight(self):
        """计算总重量"""
        return sum(float(d.weight or 0) for d in self.rebar_details)

    @property
    def weight_by_diameter(self):
        """按直径汇总重量 {6: 1.234, 8: 5.678, ...}"""
        result = {}
        for d in self.rebar_details:
            dia = int(d.diameter or 0)
            result[dia] = round(result.get(dia, 0) + float(d.weight or 0), 3)
        return result

    def __repr__(self):
        return f"<Component {self.name} type={self.component_type}>"


class RebarDetail(db.Model):
    """钢筋明细"""

    __tablename__ = "rebar_details"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    component_id = db.Column(
        db.Integer, db.ForeignKey("components.id", ondelete="CASCADE"), nullable=False
    )
    diameter = db.Column(db.Integer, nullable=False, comment="钢筋直径(mm): 6/8/10/12/14/16/18/20/22/25/28/32")
    weight = db.Column(db.DECIMAL(10, 3), nullable=False, default=0, comment="重量(吨)")
    rebar_count = db.Column(db.Integer, nullable=True, comment="根数")
    single_length = db.Column(db.DECIMAL(8, 2), nullable=True, comment="单根长度(m)")
    total_length = db.Column(db.DECIMAL(10, 2), nullable=True, comment="总长度(m)")
    source_file = db.Column(db.String(500), nullable=True, comment="来源文件名")
    batch_id = db.Column(
        db.Integer, db.ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True
    )
    remark = db.Column(db.Text, nullable=True)

    component = db.relationship("Component", back_populates="rebar_details")

    __table_args__ = (db.Index("idx_rd_component", "component_id"),
                      db.Index("idx_rd_batch", "batch_id"))

    def __repr__(self):
        return f"<RebarDetail dia={self.diameter} weight={self.weight}>"


class ImportBatch(db.Model):
    """导入批次"""

    __tablename__ = "import_batches"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.String(500), nullable=False, comment="文件名")
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    status = db.Column(
        db.Enum("pending", "processing", "done", "failed", "approved", "rejected"),
        nullable=False,
        default="pending",
        comment="状态",
    )
    reviewed_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at = db.Column(db.DateTime, nullable=True, comment="审核时间")
    review_comment = db.Column(db.Text, nullable=True, comment="审核意见")
    imported_count = db.Column(db.Integer, default=0, comment="成功导入条数")
    failed_count = db.Column(db.Integer, default=0, comment="失败条数")
    total_rows = db.Column(db.Integer, default=0, comment="总行数")
    error_detail = db.Column(db.JSON, nullable=True, comment="错误详情")
    source_path = db.Column(db.String(500), nullable=True, comment="源文件存储路径")
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project")
    creator = db.relationship("User", foreign_keys=[created_by])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (db.Index("idx_ib_project", "project_id", "created_at"),)

    def __repr__(self):
        return f"<ImportBatch {self.file_name}>"
