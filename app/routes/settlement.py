# ============================================
# 钢筋精细化管理平台 — 结算管理蓝图
# ============================================
from flask import Blueprint, render_template
from flask_login import login_required

from app.models import Project
from app.services.auth_service import project_access_required
from app.services.project_detail_service import get_settlement_analysis


settlement_bp = Blueprint("settlement", __name__, template_folder="../templates/settlement")


@settlement_bp.route("/<int:project_id>/analysis")
@login_required
@project_access_required
def analysis(project_id):
    """项目结算分析（结余率分析）"""
    project = Project.query.get_or_404(project_id)
    settlement = get_settlement_analysis(project_id)
    return render_template(
        "settlement/analysis.html",
        project=project,
        settlement=settlement,
        current_project=project,
        active_menu="settlement",
        active_submenu="analysis",
        page_title="结余率分析",
    )


@settlement_bp.route("/<int:project_id>/documents")
@login_required
@project_access_required
def documents(project_id):
    """项目结算文件"""
    project = Project.query.get_or_404(project_id)
    return render_template(
        "settlement/documents.html",
        project=project,
        current_project=project,
        active_menu="settlement",
        active_submenu="documents",
        page_title="结算文件",
    )
