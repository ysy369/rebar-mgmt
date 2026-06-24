# ============================================
# 钢筋精细化管理平台 — 首页蓝图（KPI + 工作台）
# ============================================
from datetime import datetime

from flask import Blueprint, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func as sql_func

from app import db
from app.models import ClientUnit, Contractor, Project, ProjectAnalysis, UserProject
from app.models.bom import Building, Floor, Area, Component, RebarDetail
from app.models.rebar import Incoming


home_bp = Blueprint("home", __name__, template_folder="../templates/home")


def _bc(*items):
    """构造统一面包屑：首页 + 各级节点"""
    base = [{"name": "钢筋管理平台", "url": url_for("home.index")}]
    base.extend(items)
    return base


def _get_accessible_projects():
    """获取当前用户可访问的项目"""
    query = Project.query
    if not current_user.is_admin:
        query = query.join(UserProject).filter(UserProject.user_id == current_user.id)
    return query.order_by(Project.updated_at.desc()).all()


@home_bp.route("/")
@login_required
def index():
    """首页：KPI 看板 + 筛选 + 工作台"""
    # 筛选项
    period = request.args.get("period", "").strip()
    client_id = request.args.get("client_id", type=int)
    contractor_id = request.args.get("contractor_id", type=int)
    selected_project_ids = request.args.getlist("project_ids", type=int)
    selected_status = request.args.get("status", "").strip()

    # 基础查询
    query = Project.query
    if not current_user.is_admin:
        query = query.join(UserProject).filter(UserProject.user_id == current_user.id)
    if client_id:
        query = query.filter(Project.client_unit_id == client_id)
    if contractor_id:
        query = query.filter(Project.contractor_id == contractor_id)
    if selected_status:
        query = query.filter(Project.status == selected_status)
    if selected_project_ids:
        query = query.filter(Project.id.in_(selected_project_ids))

    projects = query.order_by(Project.updated_at.desc()).all()
    project_ids = [p.id for p in projects]

    # 项目汇总维度 KPI（深色卡片）
    summary_stats = {
        "project_count": len(projects),
        "output_value": round(sum(float(p.output_value or 0) for p in projects), 2),
        "contract_amount": round(sum(float(p.contract_amount or 0) for p in projects), 2),
        "finished_count": sum(1 for p in projects if p.status == "finished"),
        "in_progress_count": sum(1 for p in projects if p.status == "in_progress"),
    }

    # 原四张白色卡片指标
    white_stats = {
        "contract_qty": 0.0,
        "usage_qty": 0.0,
        "detailing_qty": 0.0,
        "incoming_qty": 0.0,
    }
    if project_ids:
        agg = (
            db.session.query(
                sql_func.sum(ProjectAnalysis.contract_qty),
                sql_func.sum(ProjectAnalysis.usage_qty),
            )
            .filter(ProjectAnalysis.project_id.in_(project_ids))
            .first()
        )
        white_stats["contract_qty"] = round(float(agg[0] or 0), 3)
        white_stats["usage_qty"] = round(float(agg[1] or 0), 3)

        # 翻样总量 = BOM 钢筋重量合计
        white_stats["detailing_qty"] = round(float(
            db.session.query(sql_func.coalesce(sql_func.sum(RebarDetail.weight), 0))
            .join(Component).join(Area).join(Floor).join(Building)
            .filter(Building.project_id.in_(project_ids))
            .scalar()
        ), 3)

        # 进场总量
        white_stats["incoming_qty"] = round(float(
            db.session.query(sql_func.coalesce(sql_func.sum(Incoming.weigh_weight), 0))
            .filter(Incoming.project_id.in_(project_ids))
            .scalar()
        ), 3)

    # 图表数据：各项目预算/使用/节约对比
    chart_data = {
        "labels": [p.name for p in projects],
        "contract": [],
        "usage": [],
        "saved": [],
    }
    for p in projects:
        pa = p.analysis
        chart_data["contract"].append(round(float(pa.contract_qty or 0), 2) if pa else 0)
        chart_data["usage"].append(round(float(pa.usage_qty or 0), 2) if pa else 0)
        chart_data["saved"].append(round(float(pa.saved_qty or 0), 2) if pa else 0)

    # 工作台 8 入口（2行4列业务模块）
    workbench = [
        {"name": "钢筋预算", "icon": "calculator",    "url": url_for("bom.dashboard"),           "bg": "#1A3C6E"},
        {"name": "钢筋翻样", "icon": "file-earmark-text","url": url_for("bom.dashboard"),         "bg": "#1a4d8f"},
        {"name": "钢筋物资", "icon": "box-seam",       "url": url_for("project.project_list"),            "bg": "#FF7A00"},
        {"name": "策划管理", "icon": "kanban",          "url": url_for("home.index"),              "bg": "#198754"},
        {"name": "巡检台帐", "icon": "clipboard-check", "url": url_for("site.inspection"),         "bg": "#0d6efd"},
        {"name": "盈亏分析", "icon": "pie-chart",       "url": url_for("audit.profit_loss"),        "bg": "#6f42c1"},
        {"name": "结算管理", "icon": "cash-coin",       "url": url_for("audit.profit_loss"),        "bg": "#fd7e14"},
        {"name": "分包领用", "icon": "truck",          "url": url_for("labor.index"),             "bg": "#0dcaf0"},
    ]

    # 综合管理 8 入口（2行4列）
    management = [
        {"name": "策划跟踪", "icon": "diagram-3",        "url": url_for("home.index"),              "bg": "#1A3C6E"},
        {"name": "项目交底", "icon": "clipboard-data",   "url": url_for("work.index"),              "bg": "#1a4d8f"},
        {"name": "图纸答疑", "icon": "question-circle",   "url": url_for("work.index"),              "bg": "#FF7A00"},
        {"name": "扣费材料", "icon": "cash-coin",        "url": url_for("audit.comparison_calc", category="fixed"), "bg": "#dc3545"},
        {"name": "非施料单", "icon": "file-earmark-text","url": url_for("project.non_budget_sheet"),"bg": "#198754"},
        {"name": "材料计划", "icon": "calendar-check",    "url": url_for("audit.procurement_plan"),   "bg": "#0d6efd"},
        {"name": "原材库余", "icon": "box-seam",         "url": url_for("project.remaining_sheet"),  "bg": "#6f42c1"},
        {"name": "罚通联扣", "icon": "exclamation-triangle","url": url_for("labor.index"),           "bg": "#fd7e14"},
    ]

    return render_template(
        "home/index.html",
        all_projects=Project.query.order_by(Project.name).all(),
        projects=projects,
        project_ids=project_ids,
        selected_project_ids=selected_project_ids,
        selected_status=selected_status,
        period=period,
        client_id=client_id,
        contractor_id=contractor_id,
        clients=ClientUnit.query.order_by(ClientUnit.name).all(),
        contractors=Contractor.query.order_by(Contractor.name).all(),
        summary_stats=summary_stats,
        white_stats=white_stats,
        workbench=workbench,
        management=management,
        chart_data=chart_data,
        breadcrumbs=_bc(),
        page_title="首页",
    )
