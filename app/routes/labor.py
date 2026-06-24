# ============================================
# 钢筋精细化管理平台 — 劳务分包管理蓝图
# ============================================
from flask import Blueprint, render_template, url_for
from flask_login import current_user, login_required

from app.models import Project
from datetime import datetime


labor_bp = Blueprint("labor", __name__, template_folder="../templates/labor")


def _bc(*items):
    """构造统一面包屑"""
    base = [{"name": "钢筋管理平台", "url": url_for("home.index")}]
    base.extend(items)
    return base


@labor_bp.route("/")
@login_required
def index():
    """劳务分包管理深色大屏"""
    if current_user.is_admin:
        projects = Project.query.filter_by(status="in_progress").order_by(Project.name).all()
    else:
        from app.models import UserProject
        projects = Project.query.join(UserProject).filter(
            UserProject.user_id == current_user.id, Project.status == "active"
        ).order_by(Project.name).all()

    # 占位数据：单体明细
    building_details = [
        {
            "name": "1#楼",
            "income_upper": 120.5,
            "budget": 115.0,
            "detailing": 118.2,
            "measure": 3.5,
            "secondary": 2.1,
            "report_upper": 60.0,
            "report_lower": 58.5,
            "settlement_upper": 119.0,
            "settlement_lower": 117.5,
            "diff": 1.5,
        },
        {
            "name": "2#楼",
            "income_upper": 98.0,
            "budget": 95.0,
            "detailing": 96.8,
            "measure": 2.8,
            "secondary": 1.5,
            "report_upper": 48.0,
            "report_lower": 47.2,
            "settlement_upper": 97.5,
            "settlement_lower": 96.0,
            "diff": 0.5,
        },
    ]

    # 占位数据：盈亏罚扣（左右两组）
    profit_penalty_left = [
        {"team": "甲分包", "penalty": 1200.0, "budget": 210.0, "usage": 205.5, "profit": 4.5},
        {"team": "乙分包", "penalty": 800.0, "budget": 180.0, "usage": 182.0, "profit": -2.0},
    ]
    profit_penalty_right = [
        {"team": "丙分包", "penalty": 500.0, "budget": 150.0, "usage": 148.5, "profit": 1.5},
        {"team": "丁分包", "penalty": 300.0, "budget": 130.0, "usage": 131.0, "profit": -1.0},
    ]

    # 占位数据：总结算量 / 报量预警
    summary = {"total_settlement": 216.5, "total_report": 105.7, "warning_count": 1}

    return render_template(
        "labor/fullscreen.html",
        projects=projects,
        building_details=building_details,
        profit_penalty_left=profit_penalty_left,
        profit_penalty_right=profit_penalty_right,
        summary=summary,
        project_note="2025年3月15日",
        duration_note="362",
        completion_note="2026年3月15日",
        area_note="52,500.00m²",
        current_date=datetime.utcnow().date(),
        page_title="劳务分包管理",
    )
