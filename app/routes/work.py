# ============================================
# 钢筋精细化管理平台 — 工作管理蓝图
# ============================================
from flask import Blueprint, render_template, request, url_for
from flask_login import login_required


work_bp = Blueprint("work", __name__, template_folder="../templates/work")


def _bc(*items):
    """构造统一面包屑"""
    base = [{"name": "钢筋管理平台", "url": url_for("home.index")}]
    base.extend(items)
    return base


@work_bp.route("/")
@login_required
def index():
    active_tab = request.args.get("tab", "responsibility")
    if active_tab not in ("responsibility", "plan", "standard"):
        active_tab = "responsibility"
    return render_template(
        "work/index.html",
        active_tab=active_tab,
        breadcrumbs=_bc({"name": "工作管理", "url": None}),
        page_title="工作管理",
    )
