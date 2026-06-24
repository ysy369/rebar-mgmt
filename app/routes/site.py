# ============================================
# 钢筋精细化管理平台 — 现场管理蓝图
# ============================================
from flask import Blueprint, render_template, url_for
from flask_login import login_required


site_bp = Blueprint("site", __name__, template_folder="../templates/site")


def _bc(*items):
    """构造统一面包屑"""
    base = [{"name": "钢筋管理平台", "url": url_for("home.index")}]
    base.extend(items)
    return base


@site_bp.route("/visual-progress")
@login_required
def visual_progress():
    return render_template(
        "site/visual_progress.html",
        active_menu="site",
        active_submenu="visual_progress",
        breadcrumbs=_bc({"name": "现场管理", "url": None}, {"name": "形象进度", "url": None}),
        page_title="形象进度",
    )


@site_bp.route("/material-issue")
@login_required
def material_issue():
    return render_template(
        "site/material_issue.html",
        active_menu="site",
        active_submenu="material_issue",
        breadcrumbs=_bc({"name": "现场管理", "url": None}, {"name": "钢筋物资领用", "url": None}),
        page_title="钢筋物资领用",
    )


@site_bp.route("/inspection")
@login_required
def inspection():
    return render_template(
        "site/inspection.html",
        active_menu="site",
        active_submenu="inspection",
        breadcrumbs=_bc({"name": "现场管理", "url": None}, {"name": "巡检管理", "url": None}),
        page_title="巡检管理",
    )


@site_bp.route("/rebar-replacement")
@login_required
def rebar_replacement():
    return render_template(
        "site/rebar_replacement.html",
        active_menu="site",
        active_submenu="rebar_replacement",
        breadcrumbs=_bc({"name": "现场管理", "url": None}, {"name": "钢筋代换", "url": None}),
        page_title="钢筋代换",
    )


@site_bp.route("/optimization-ledger")
@login_required
def optimization_ledger():
    return render_template(
        "site/optimization_ledger.html",
        active_menu="site",
        active_submenu="optimization_ledger",
        breadcrumbs=_bc({"name": "现场管理", "url": None}, {"name": "钢筋优化台账", "url": None}),
        page_title="钢筋优化台账",
    )
