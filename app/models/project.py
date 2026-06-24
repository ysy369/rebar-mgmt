# ============================================
# 钢筋精细化管理平台 — 项目/甲方模型
# ============================================
from datetime import datetime

from app import db


class ClientUnit(db.Model):
    """甲方单位"""

    __tablename__ = "client_units"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    projects = db.relationship("Project", back_populates="client_unit", lazy="dynamic")

    def __repr__(self):
        return f"<ClientUnit {self.name}>"


class Project(db.Model):
    """项目表"""

    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False, comment="项目名称")
    contract_name = db.Column(
        db.String(300), nullable=True, comment="合同名称"
    )
    contract_no = db.Column(
        db.String(100), nullable=True, comment="合同编号"
    )
    project_name = db.Column(
        db.String(255), nullable=True, comment="工程名称"
    )
    total_contractor_name = db.Column(
        db.String(255), nullable=True, comment="总包单位名称"
    )
    client_unit_id = db.Column(
        db.Integer, db.ForeignKey("client_units.id", ondelete="SET NULL"), nullable=True
    )
    contractor_id = db.Column(
        db.Integer,
        db.ForeignKey("contractors.id", ondelete="SET NULL"),
        nullable=True,
        comment="承接公司ID",
    )
    description = db.Column(db.Text, nullable=True, comment="项目描述")
    start_date = db.Column(db.Date, nullable=True, comment="开工日期")
    duration_days = db.Column(db.Integer, nullable=True, comment="总工期(天)")
    est_rebar_total = db.Column(
        db.DECIMAL(15, 3), nullable=True, comment="预估钢筋总量(T)"
    )
    building_area = db.Column(
        db.DECIMAL(12, 2), nullable=True, comment="建筑面积(m²)"
    )
    rebar_content = db.Column(
        db.DECIMAL(10, 3), nullable=True, comment="钢筋含量(kg/m²)"
    )
    project_location = db.Column(
        db.String(500), nullable=True, comment="工程地点"
    )
    service_scope = db.Column(
        db.Text, nullable=True, comment="服务范围"
    )
    service_content = db.Column(
        db.Text, nullable=True, comment="服务内容"
    )
    service_duration = db.Column(
        db.Integer, nullable=True, comment="服务工期(天)"
    )
    contract_amount = db.Column(
        db.DECIMAL(14, 2), nullable=True, comment="合同额(万元)"
    )
    output_value = db.Column(
        db.DECIMAL(14, 2), nullable=True, comment="累计产值(万元)"
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="in_progress",
        comment="项目状态: finished=已完工,in_progress=在建,not_started=未开工,stopped=停工",
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    # 关系
    client_unit = db.relationship("ClientUnit", back_populates="projects")
    contractor = db.relationship("Contractor", back_populates="projects")
    user_projects = db.relationship(
        "UserProject", back_populates="project", lazy="dynamic"
    )
    analysis = db.relationship(
        "ProjectAnalysis",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
    imported_files = db.relationship(
        "ImportedFile", back_populates="project", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project {self.name}>"


class UserProject(db.Model):
    """用户-项目授权关联表"""

    __tablename__ = "user_projects"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    role = db.Column(
        db.Enum("engineer", "reviewer", "viewer"),
        nullable=False,
        default="engineer",
        comment="成员角色：engineer=精管工程师, reviewer=审核员, viewer=查看员",
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="添加时间")

    # 复合唯一索引
    __table_args__ = (
        db.UniqueConstraint("user_id", "project_id", name="uq_user_project"),
    )

    # 关系
    user = db.relationship("User", back_populates="user_projects")
    project = db.relationship("Project", back_populates="user_projects")

    def __repr__(self):
        return f"<UserProject user={self.user_id} project={self.project_id}>"
