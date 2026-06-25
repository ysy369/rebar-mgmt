# ============================================
# 钢筋精细化管理平台 — 管理端蓝图
# ============================================
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import extract, func as sql_func
from sqlalchemy.orm import joinedload

from app import db
from app.models import ClientUnit, Contractor, Project, ProjectAnalysis, User
from app.models.bom import Building, Floor, Area, Component, RebarDetail, ImportBatch
from app.models.business import ProjectCost
from app.models.rebar import Incoming, Transfer, MeasureRebar, Inventory, Waste
from app.services.auth_service import admin_required
from app.services.cutting_order_service import get_all_orders, get_order_by_id, get_order_items, mark_reviewed
from app.services.pl_service import get_all_projects_pl
from app.services.contractor_service import (
    create_client_unit,
    create_contractor,
    create_project,
    delete_client_unit,
    delete_contractor,
    delete_project,
    get_all_client_units,
    get_all_contractors,
    get_all_projects,
    get_client_unit_by_id,
    get_contractor_by_id,
    get_project_by_id,
    update_client_unit,
    update_contractor,
    update_project,
)
from app.services.pagination_service import paginate, get_page

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


def _bc(*items):
    """构造统一面包屑：首页 + 各级节点"""
    base = [{"name": "钢筋管理平台", "url": url_for("home.index")}]
    base.extend(items)
    return base


def _get_project_bom_stats(project_ids):
    """批量获取项目的 BOM 统计：{project_id: (component_count, tonnage)}"""
    if not project_ids:
        return {}
    component_counts = dict(
        db.session.query(Building.project_id, sql_func.count(Component.id))
        .join(Floor).join(Area).join(Component)
        .filter(Building.project_id.in_(project_ids))
        .group_by(Building.project_id)
        .all()
    )
    tonnages = dict(
        db.session.query(Building.project_id, sql_func.sum(RebarDetail.weight))
        .join(Floor).join(Area).join(Component).join(RebarDetail)
        .filter(Building.project_id.in_(project_ids))
        .group_by(Building.project_id)
        .all()
    )
    return {
        pid: (
            component_counts.get(pid, 0),
            round(float(tonnages.get(pid, 0) or 0), 3)
        )
        for pid in project_ids
    }


def _calc_monthly_stats(year: int, month: int):
    """计算指定月份的全局月度指标（从原始台账汇总）"""
    incoming = round(float(
        db.session.query(sql_func.coalesce(sql_func.sum(Incoming.weigh_weight), 0))
        .filter(extract("year", Incoming.date) == year, extract("month", Incoming.date) == month)
        .scalar()
    ), 1)

    transfer_out = round(float(
        db.session.query(sql_func.coalesce(sql_func.sum(Transfer.weight), 0))
        .filter(Transfer.direction == "out", extract("year", Transfer.date) == year, extract("month", Transfer.date) == month)
        .scalar()
    ), 1)

    waste = round(float(
        db.session.query(sql_func.coalesce(sql_func.sum(Waste.waste_weight), 0))
        .filter(extract("year", Waste.process_date) == year, extract("month", Waste.process_date) == month)
        .scalar()
    ), 1)

    remaining = round(float(
        db.session.query(sql_func.coalesce(sql_func.sum(Inventory.total_weight), 0))
        .filter(extract("year", Inventory.inventory_date) == year, extract("month", Inventory.inventory_date) == month)
        .scalar()
    ), 1)

    measure_kg = float(
        db.session.query(sql_func.coalesce(sql_func.sum(MeasureRebar.weight_kg), 0))
        .filter(extract("year", MeasureRebar.date) == year, extract("month", MeasureRebar.date) == month)
        .scalar()
    )
    measure = round(measure_kg / 1000, 3)

    # 月度使用量 = 进场 - 剩余 - 废料 - 调拨 - 措施筋（均转换为吨）
    usage = round(incoming - remaining - waste - transfer_out - measure, 3)

    # 损耗率
    loss_rate = round((waste / incoming * 100) if incoming > 0 else 0, 2)

    # 月度效益率：以全期预算作为月度预算参考
    total_contract = round(float(
        db.session.query(sql_func.coalesce(sql_func.sum(ProjectAnalysis.contract_qty), 0)).scalar()
    ), 1)
    saved = round(total_contract - usage, 3)
    efficiency_rate = round((saved / total_contract * 100) if total_contract > 0 else 0, 2)

    return {
        "incoming": incoming,
        "transfer_out": transfer_out,
        "waste": waste,
        "remaining": remaining,
        "measure": measure,
        "usage": usage,
        "saved": saved,
        "loss_rate": loss_rate,
        "efficiency_rate": efficiency_rate,
        "contract_qty": total_contract,
        "balance_rate": efficiency_rate,
    }


@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    """管理端首页 — 已迁移至 /home，此处做重定向"""
    return redirect(url_for("home.index"))


# ========== 承接公司 CRUD ==========

@admin_bp.route("/contractors")
@login_required
@admin_required
def contractor_list():
    pagination = paginate(
        Contractor.query.order_by(Contractor.name),
        per_page=20
    )
    return render_template(
        "admin/contractors/list.html",
        pagination=pagination,
        breadcrumbs=_bc({"name": "项目管理", "url": None}, {"name": "承接公司", "url": None}),
        page_title="承接公司",
    )


@admin_bp.route("/contractors/create", methods=["GET", "POST"])
@login_required
@admin_required
def contractor_create():
    if request.method == "POST":
        try:
            create_contractor(
                name=request.form["name"],
                contact_person=request.form.get("contact_person"),
                contact_phone=request.form.get("contact_phone"),
                address=request.form.get("address"),
                remark=request.form.get("remark"),
            )
            flash("承接公司创建成功。", "success")
            return redirect(url_for("admin.contractor_list"))
        except Exception as e:
            flash(f"创建失败: {str(e)}", "danger")
    return render_template(
        "admin/contractors/form.html",
        contractor=None,
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": "承接公司", "url": url_for("admin.contractor_list")},
            {"name": "创建承接公司", "url": None},
        ),
        page_title="创建承接公司",
    )


@admin_bp.route("/contractors/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def contractor_edit(id):
    contractor = get_contractor_by_id(id)
    if request.method == "POST":
        try:
            update_contractor(
                id,
                name=request.form["name"],
                contact_person=request.form.get("contact_person"),
                contact_phone=request.form.get("contact_phone"),
                address=request.form.get("address"),
                remark=request.form.get("remark"),
            )
            flash("承接公司更新成功。", "success")
            return redirect(url_for("admin.contractor_list"))
        except Exception as e:
            flash(f"更新失败: {str(e)}", "danger")
    return render_template(
        "admin/contractors/form.html",
        contractor=contractor,
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": "承接公司", "url": url_for("admin.contractor_list")},
            {"name": "编辑承接公司", "url": None},
        ),
        page_title="编辑承接公司",
    )


@admin_bp.route("/contractors/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def contractor_delete(id):
    try:
        delete_contractor(id)
        flash("承接公司已删除。", "success")
    except Exception as e:
        flash(f"删除失败: {str(e)}", "danger")
    return redirect(url_for("admin.contractor_list"))


# ========== 甲方单位 CRUD ==========

@admin_bp.route("/client-units")
@login_required
@admin_required
def client_unit_list():
    pagination = paginate(
        ClientUnit.query.order_by(ClientUnit.name),
        per_page=20
    )
    return render_template(
        "admin/client_units/list.html",
        pagination=pagination,
        breadcrumbs=_bc({"name": "项目管理", "url": None}, {"name": "甲方单位", "url": None}),
        page_title="甲方单位",
    )


@admin_bp.route("/client-units/create", methods=["GET", "POST"])
@login_required
@admin_required
def client_unit_create():
    if request.method == "POST":
        try:
            create_client_unit(name=request.form["name"])
            flash("甲方单位创建成功。", "success")
            return redirect(url_for("admin.client_unit_list"))
        except Exception as e:
            flash(f"创建失败: {str(e)}", "danger")
    return render_template(
        "admin/client_units/form.html",
        unit=None,
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": "甲方单位", "url": url_for("admin.client_unit_list")},
            {"name": "创建甲方单位", "url": None},
        ),
        page_title="创建甲方单位",
    )


@admin_bp.route("/client-units/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def client_unit_edit(id):
    unit = get_client_unit_by_id(id)
    if request.method == "POST":
        try:
            update_client_unit(id, name=request.form["name"])
            flash("甲方单位更新成功。", "success")
            return redirect(url_for("admin.client_unit_list"))
        except Exception as e:
            flash(f"更新失败: {str(e)}", "danger")
    return render_template(
        "admin/client_units/form.html",
        unit=unit,
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": "甲方单位", "url": url_for("admin.client_unit_list")},
            {"name": "编辑甲方单位", "url": None},
        ),
        page_title="编辑甲方单位",
    )


@admin_bp.route("/client-units/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def client_unit_delete(id):
    try:
        delete_client_unit(id)
        flash("甲方单位已删除。", "success")
    except Exception as e:
        flash(f"删除失败: {str(e)}", "danger")
    return redirect(url_for("admin.client_unit_list"))


# ========== 项目管理 CRUD ==========

@admin_bp.route("/projects")
@login_required
@admin_required
def project_list():
    pagination = paginate(
        Project.query.options(
            joinedload(Project.client_unit),
            joinedload(Project.contractor),
        ).order_by(Project.updated_at.desc()),
        per_page=20
    )
    clients = get_all_client_units()
    contractors = get_all_contractors()
    return render_template(
        "admin/projects/list.html",
        pagination=pagination,
        clients=clients,
        contractors=contractors,
        breadcrumbs=_bc({"name": "项目管理", "url": None}, {"name": "项目列表", "url": None}),
        page_title="项目列表",
    )


@admin_bp.route("/projects/create", methods=["GET", "POST"])
@login_required
@admin_required
def project_create():
    if request.method == "POST":
        try:
            create_project(
                name=request.form["name"],
                contract_name=request.form.get("contract_name"),
                contract_no=request.form.get("contract_no"),
                project_name=request.form.get("project_name"),
                total_contractor_name=request.form.get("total_contractor_name"),
                client_unit_id=request.form.get("client_unit_id", type=int),
                contractor_id=request.form.get("contractor_id", type=int),
                description=request.form.get("description"),
                start_date=request.form.get("start_date") or None,
                duration_days=request.form.get("duration_days", type=int),
                est_rebar_total=request.form.get("est_rebar_total", type=float),
                building_area=request.form.get("building_area", type=float),
                rebar_content=request.form.get("rebar_content", type=float),
                project_location=request.form.get("project_location"),
                service_scope=request.form.get("service_scope"),
                service_content=request.form.get("service_content"),
                service_duration=request.form.get("service_duration", type=int),
            )
            flash("项目创建成功。", "success")
            return redirect(url_for("admin.project_list"))
        except Exception as e:
            flash(f"创建失败: {str(e)}", "danger")
    clients = get_all_client_units()
    contractors = get_all_contractors()
    return render_template(
        "admin/projects/form.html",
        project=None,
        clients=clients,
        contractors=contractors,
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": "创建项目", "url": None},
        ),
        page_title="创建项目",
    )


@admin_bp.route("/projects/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def project_edit(id):
    project = get_project_by_id(id)
    if request.method == "POST":
        try:
            update_project(
                id,
                name=request.form["name"],
                contract_name=request.form.get("contract_name"),
                contract_no=request.form.get("contract_no"),
                project_name=request.form.get("project_name"),
                total_contractor_name=request.form.get("total_contractor_name"),
                client_unit_id=request.form.get("client_unit_id", type=int),
                contractor_id=request.form.get("contractor_id", type=int),
                description=request.form.get("description"),
                status=request.form.get("status"),
                start_date=request.form.get("start_date") or None,
                duration_days=request.form.get("duration_days", type=int),
                est_rebar_total=request.form.get("est_rebar_total", type=float),
                building_area=request.form.get("building_area", type=float),
                rebar_content=request.form.get("rebar_content", type=float),
                project_location=request.form.get("project_location"),
                service_scope=request.form.get("service_scope"),
                service_content=request.form.get("service_content"),
                service_duration=request.form.get("service_duration", type=int),
            )
            flash("项目更新成功。", "success")
            return redirect(url_for("admin.project_list"))
        except Exception as e:
            flash(f"更新失败: {str(e)}", "danger")
    clients = get_all_client_units()
    contractors = get_all_contractors()
    return render_template(
        "admin/projects/form.html",
        project=project,
        clients=clients,
        contractors=contractors,
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": "编辑项目", "url": None},
        ),
        page_title="编辑项目",
    )


@admin_bp.route("/projects/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def project_delete(id):
    try:
        delete_project(id)
        flash("项目已删除。", "success")
    except Exception as e:
        flash(f"删除失败: {str(e)}", "danger")
    return redirect(url_for("admin.project_list"))


# ========== 料单审核 ==========

@admin_bp.route("/cutting-orders")
@login_required
@admin_required
def cutting_order_list():
    """管理员查看所有料单"""
    status = request.args.get("status")
    project_id = request.args.get("project_id", type=int)
    query = get_all_orders({"status": status, "project_id": project_id} if status or project_id else None)
    pagination = paginate(query, per_page=20)
    projects = get_all_projects()
    return render_template("admin/cutting_orders/list.html",
                          pagination=pagination,
                          projects=projects,
                          current_status=status,
                          current_project_id=project_id,
                          breadcrumbs=_bc({"name": "审核与分析", "url": None}, {"name": "料单审核", "url": None}),
                          page_title="料单审核")


@admin_bp.route("/cutting-orders/<int:order_id>")
@login_required
@admin_required
def cutting_order_detail(order_id):
    """审核料单详情"""
    order = get_order_by_id(order_id)
    items = get_order_items(order_id)
    project = Project.query.get(order.project_id)
    return render_template(
        "admin/cutting_orders/detail.html",
        order=order,
        items=items,
        project=project,
        breadcrumbs=_bc(
            {"name": "审核与分析", "url": url_for("admin.cutting_order_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "料单详情", "url": None},
        ),
        page_title="料单详情",
    )


@admin_bp.route("/cutting-orders/<int:order_id>/review", methods=["POST"])
@login_required
@admin_required
def cutting_order_review(order_id):
    """审核操作"""
    action = request.form.get("action")
    comment = request.form.get("comment", "")
    try:
        if action == "reviewed":
            mark_reviewed(order_id, current_user.id)
            flash("已标记为已审核。", "success")
        elif action in ("approved", "rejected"):
            from app.services.cutting_order_service import review_order
            review_order(order_id, action, current_user.id, comment)
            flash("审核完成。", "success")
        else:
            flash("无效操作。", "danger")
    except Exception as e:
        flash(f"操作失败: {e}", "danger")
    return redirect(url_for("admin.cutting_order_detail", order_id=order_id))


# ========== 跨项目盈亏 ==========

@admin_bp.route("/recalc-all")
@login_required
@admin_required
def recalc_all():
    """重新计算所有项目的分析数据"""
    from app.services.analysis_service import recalc_project_analysis
    projects = Project.query.filter_by(status="in_progress").all()
    success_count = 0
    for p in projects:
        try:
            recalc_project_analysis(p.id)
            success_count += 1
        except Exception as e:
            # 记录日志但不阻断整体流程
            import logging
            logging.getLogger(__name__).warning(f"重新计算项目 {p.id} 失败: {e}")
    flash(f"已刷新 {success_count}/{len(projects)} 个项目的分析数据。", "success")
    return redirect(url_for("home.index"))


@admin_bp.route("/pl-dashboard")
@login_required
@admin_required
def pl_dashboard():
    """跨项目盈亏看板"""
    data = get_all_projects_pl()
    total_profit = sum(d["pl"].net_profit or 0 for d in data)
    total_income = sum(d["pl"].total_income or 0 for d in data)
    total_cost = sum(d["pl"].total_cost or 0 for d in data)
    return render_template("admin/pl_analysis/dashboard.html",
                          data=data, total_profit=total_profit,
                          total_income=total_income, total_cost=total_cost,
                          breadcrumbs=_bc({"name": "审核与分析", "url": None}, {"name": "盈亏分析", "url": None}),
                          page_title="盈亏分析")


# ========== 用户管理 ==========

@admin_bp.route("/users")
@login_required
@admin_required
def user_list():
    """用户列表"""
    pagination = paginate(
        User.query.order_by(User.role, User.username),
        per_page=20
    )
    return render_template(
        "admin/users/list.html",
        pagination=pagination,
        breadcrumbs=_bc({"name": "系统设置", "url": None}, {"name": "用户管理", "url": None}),
        page_title="用户管理",
    )


@admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def user_create():
    """创建用户"""
    if request.method == "POST":
        try:
            username = request.form["username"].strip()
            password = request.form["password"]
            display_name = request.form["display_name"].strip()
            role = request.form.get("role", "user")

            if User.query.filter_by(username=username).first():
                flash("账号已存在。", "danger")
                return render_template(
                    "admin/users/form.html",
                    user=None,
                    breadcrumbs=_bc(
                        {"name": "系统设置", "url": url_for("admin.user_list")},
                        {"name": "创建用户", "url": None},
                    ),
                    page_title="创建用户",
                )

            user = User(username=username, display_name=display_name, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f"用户 {username} 创建成功。", "success")
            return redirect(url_for("admin.user_list"))
        except Exception as e:
            flash("创建失败，请重试。", "danger")
    return render_template(
        "admin/users/form.html",
        user=None,
        breadcrumbs=_bc(
            {"name": "系统设置", "url": url_for("admin.user_list")},
            {"name": "创建用户", "url": None},
        ),
        page_title="创建用户",
    )


@admin_bp.route("/users/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def user_edit(id):
    """编辑用户"""
    user = User.query.get_or_404(id)
    if request.method == "POST":
        try:
            user.display_name = request.form["display_name"].strip()
            user.role = request.form.get("role", "user")

            new_password = request.form.get("password")
            if new_password:
                user.set_password(new_password)

            db.session.commit()
            flash(f"用户 {user.username} 更新成功。", "success")
            return redirect(url_for("admin.user_list"))
        except Exception as e:
            flash("更新失败，请重试。", "danger")
    return render_template(
        "admin/users/form.html",
        user=user,
        breadcrumbs=_bc(
            {"name": "系统设置", "url": url_for("admin.user_list")},
            {"name": "编辑用户", "url": None},
        ),
        page_title="编辑用户",
    )


@admin_bp.route("/users/<int:id>/toggle", methods=["POST"])
@login_required
@admin_required
def user_toggle(id):
    """启用/禁用用户"""
    user = User.query.get_or_404(id)
    user.is_active = not user.is_active
    db.session.commit()
    status = "启用" if user.is_active else "禁用"
    flash(f"用户 {user.username} 已{status}。", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def user_delete(id):
    """删除用户"""
    user = User.query.get_or_404(id)
    if user.username == "admin":
        flash("不能删除内置管理员。", "danger")
        return redirect(url_for("admin.user_list"))
    db.session.delete(user)
    db.session.commit()
    flash(f"用户 {user.username} 已删除。", "success")
    return redirect(url_for("admin.user_list"))
