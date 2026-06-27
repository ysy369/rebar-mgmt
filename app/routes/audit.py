# ============================================
# 钢筋精细化管理平台 — 审核与分析蓝图
# ============================================
from flask import Blueprint, render_template, request, url_for
from flask_login import login_required


audit_bp = Blueprint("audit", __name__, template_folder="../templates/audit")


def _bc(*items):
    """构造统一面包屑"""
    base = [{"name": "钢筋管理平台", "url": url_for("home.index")}]
    base.extend(items)
    return base


@audit_bp.route("/profit-loss")
@login_required
def profit_loss():
    return render_template(
        "audit/profit_loss.html",
        active_menu="audit",
        active_submenu="profit_loss",
        breadcrumbs=_bc({"name": "审核与分析", "url": None}, {"name": "盈亏分析", "url": None}),
        page_title="盈亏分析",
    )


@audit_bp.route("/data-dynamic")
@login_required
def data_dynamic():
    return render_template(
        "audit/data_dynamic.html",
        active_menu="audit",
        active_submenu="data_dynamic",
        breadcrumbs=_bc({"name": "审核与分析", "url": None}, {"name": "数据动态管理分析", "url": None}),
        page_title="数据动态管理分析",
    )


@audit_bp.route("/procurement-plan")
@login_required
def procurement_plan():
    return render_template(
        "audit/procurement_plan.html",
        active_menu="audit",
        active_submenu="procurement_plan",
        breadcrumbs=_bc({"name": "审核与分析", "url": None}, {"name": "钢筋采购计划", "url": None}),
        page_title="钢筋采购计划",
    )


@audit_bp.route("/cutting-order-audit")
@login_required
def cutting_order_audit():
    return render_template(
        "audit/cutting_order_audit.html",
        active_menu="audit",
        active_submenu="cutting_order_audit",
        breadcrumbs=_bc({"name": "审核与分析", "url": None}, {"name": "料单审核台账", "url": None}),
        page_title="料单审核台账",
    )


@audit_bp.route("/comparison-calc")
@login_required
def comparison_calc():
    category = request.args.get("category", "coil")
    category_titles = {
        "coil": "盘螺对比",
        "fixed": "定尺余料对比",
        "threshold": "余料临界值",
    }
    return render_template(
        "audit/comparison_calc.html",
        active_menu="audit",
        active_submenu="comparison_calc",
        category=category,
        category_title=category_titles.get(category, "钢筋对比测算"),
        breadcrumbs=_bc(
            {"name": "审核与分析", "url": None},
            {"name": "钢筋对比测算", "url": None},
            {"name": category_titles.get(category, ""), "url": None},
        ),
        page_title=category_titles.get(category, "钢筋对比测算"),
    )
