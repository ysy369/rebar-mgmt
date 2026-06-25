# ============================================
# 钢筋精细化管理平台 — 项目端蓝图 (完整版)
# ============================================
import os
from datetime import datetime, timedelta
from flask import abort, Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_, extract, func as sql_func
from werkzeug.utils import secure_filename
from app import db
from app.models import ImportedFile, Project, ProjectAnalysis, ProjectAttachment, UserProject
from app.models.bom import ImportBatch, RebarDetail
from app.models.rebar import Incoming, Transfer, MeasureRebar, Inventory, Waste
from app.services.auth_service import project_access_required
from app.services.pagination_service import paginate
from app.routes.dashboard import (
    _build_alerts,
    _calc_all_period_stats,
    _calc_material_indices,
    _calc_monthly_trend,
    _calc_period_stats,
    _kpi_status,
    _parse_date_range,
)
from app.services.attachment_service import (
    delete_attachment, get_project_attachments, save_attachment, set_cover, validate_image,
)
from app.services.cutting_order_service import (
    get_project_orders, get_order_by_id, create_order, update_order, delete_order,
    get_order_items, add_order_item, update_order_item, delete_order_item,
    submit_order, mark_reviewed, review_order,
)
from app.services.cost_service import (
    get_project_costs, get_cost_summary, get_cost_by_id,
    create_cost, update_cost, delete_cost, CATEGORY_LABELS,
)
from app.services.pl_service import (
    get_project_pl, update_unit_price, update_other_income,
)
from app.services.project_detail_service import (
    MEMBER_ROLE_MAP,
    add_project_member,
    export_settlement_analysis,
    get_available_users,
    get_ledger_summary,
    get_profit_analysis,
    get_project_members,
    get_project_overview,
    get_settlement_analysis,
    remove_project_member,
)
from app.services.auth_service import can_access_project

def _can_manage_members(project_id):
    """仅 admin 或项目成员可管理项目人员"""
    if current_user.is_admin:
        return True
    return UserProject.query.filter_by(
        project_id=project_id, user_id=current_user.id
    ).first() is not None

project_bp = Blueprint("project", __name__, template_folder="../templates/project")


def _bc(*items):
    """构造统一面包屑：首页 + 各级节点"""
    base = [{"name": "钢筋管理平台", "url": url_for("home.index")}]
    base.extend(items)
    return base


@project_bp.route("/list")
@login_required
def project_list():
    if current_user.is_admin:
        projects = Project.query.filter_by(status="in_progress").order_by(Project.updated_at.desc()).all()
    else:
        projects = Project.query.join(UserProject).filter(
            UserProject.user_id == current_user.id, Project.status == "in_progress"
        ).order_by(Project.updated_at.desc()).all()

    # 批量聚合 BOM 统计
    project_ids = [p.id for p in projects]
    component_counts = {}
    tonnages = {}
    if project_ids:
        from app.models.bom import Building, Floor, Area, Component, RebarDetail
        from sqlalchemy import func as sql_func
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
    for p in projects:
        p.bom_components = component_counts.get(p.id, 0)
        p.bom_tonnage = round(float(tonnages.get(p.id, 0) or 0), 3)

    return render_template(
        "project/list.html",
        projects=projects,
        breadcrumbs=_bc(
            {"name": "项目管理", "url": None},
            {"name": "项目列表", "url": None},
        ),
        page_title="项目列表",
    )


# ===== 深色看板辅助函数 =====

def _get_dashboard_projects():
    """获取当前用户可访问的项目"""
    query = Project.query.filter_by(status="in_progress")
    if not current_user.is_admin:
        query = query.join(UserProject).filter(UserProject.user_id == current_user.id)
    return query.order_by(Project.updated_at.desc()).all()


def _get_dashboard_kpi_status(value, metric):
    """复用看板 KPI 状态判断"""
    return _kpi_status(value, metric)


@project_bp.route("/dashboard")
@login_required
def dashboard():
    """项目数据看板 — 深色科技大屏（三栏布局）"""
    period = request.args.get("period", "all").strip()
    if period not in ("all", "month", "quarter", "year", "custom"):
        period = "all"
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    date_from, date_to, period_label = _parse_date_range(period, start_date, end_date)

    projects = _get_dashboard_projects()
    project_ids = [p.id for p in projects]

    # 全期指标（始终展示）
    all_stats = _calc_all_period_stats(project_ids)
    all_material = _calc_material_indices(project_ids)

    # 选中周期指标
    if period == "all":
        selected_stats = all_stats
        material_selected = all_material
    else:
        selected_stats = _calc_period_stats(project_ids, date_from, date_to)
        material_selected = _calc_material_indices(project_ids, date_from, date_to)

    # 上月指标（前期对比）
    now = datetime.utcnow()
    prev_month = now.month - 1 if now.month > 1 else 12
    prev_year = now.year if now.month > 1 else now.year - 1
    prev_from = datetime(prev_year, prev_month, 1)
    if prev_month == 12:
        prev_to = datetime(prev_year + 1, 1, 1) - timedelta(seconds=1)
    else:
        prev_to = datetime(prev_year, prev_month + 1, 1) - timedelta(seconds=1)
    prev_stats = _calc_period_stats(project_ids, prev_from, prev_to)
    prev_material = _calc_material_indices(project_ids, prev_from, prev_to)

    # 趋势
    trend = _calc_monthly_trend(project_ids)

    # 预警
    alerts = _build_alerts(project_ids)

    # KPI 状态标签
    def _make_status(stats):
        usage_ratio = stats["usage_qty"] / stats["contract_qty"] if stats["contract_qty"] > 0 else 0
        return {
            "usage_label": _kpi_status(usage_ratio, "usage")[0],
            "usage_class": _kpi_status(usage_ratio, "usage")[1],
            "loss_label": _kpi_status(stats["loss_rate"], "loss_rate")[0],
            "loss_class": _kpi_status(stats["loss_rate"], "loss_rate")[1],
            "efficiency_label": _kpi_status(stats["efficiency_rate"], "efficiency_rate")[0],
            "efficiency_class": _kpi_status(stats["efficiency_rate"], "efficiency_rate")[1],
        }

    selected_status = _make_status(selected_stats)
    all_status = _make_status(all_stats)
    prev_status = _make_status(prev_stats)

    # 周期标签
    period_labels = {
        "all": "周期累计",
        "month": "本月",
        "quarter": "本季度",
        "year": "本年",
        "custom": "自定义",
    }

    return render_template(
        "dashboard/index.html",
        projects=projects,
        project_ids=project_ids,
        all_dashboard_projects=Project.query.order_by(Project.name).all(),
        selected_project_ids=request.args.getlist("project_ids", type=int),
        current_period=period,
        period_label=period_labels.get(period, period_label),
        period_label_all=period_labels.get(period, period_label),
        start_date=start_date,
        end_date=end_date,
        current_date=datetime.utcnow().date(),
        # 全期
        all_stats=all_stats,
        all_status=all_status,
        material_all=all_material,
        # 选中周期
        selected_stats=selected_stats,
        selected_status=selected_status,
        material_selected=material_selected,
        # 前期
        prev_stats=prev_stats,
        prev_status=prev_status,
        material_prev=prev_material,
        prev_label=f"{prev_year}年{prev_month}月",
        # 趋势 & 预警
        trend=trend,
        alerts=alerts,
        # 导航菜单（顶部横向）
        nav_menu=[
            {"name": "数据看板", "url": url_for("project.dashboard"), "active": True, "visible": True},
            {"name": "钢筋台账", "url": url_for("project.project_list"), "active": False, "visible": True},
            {"name": "方样料单", "url": url_for("bom.dashboard"), "active": False, "visible": True},
            {"name": "项目管理", "url": url_for("admin.project_list"), "active": False, "visible": current_user.is_admin},
            {"name": "料单审核", "url": url_for("admin.cutting_order_list"), "active": False, "visible": current_user.is_admin},
            {"name": "盈亏分析", "url": url_for("admin.pl_dashboard"), "active": False, "visible": current_user.is_admin},
        ],
        breadcrumbs=_bc({"name": "项目数据看板", "url": None}),
        page_title="项目数据看板",
    )


# ========== 项目表单页（空壳） ==========

def _render_sheet(view_name):
    """通用渲染项目表单页（文件列表）"""
    ledger_type = SHEET_LEDGER_MAP.get(view_name)
    page_title = LEDGER_TYPE_LABELS.get(ledger_type, view_name)
    search = request.args.get("search", "").strip()
    query = _get_imported_files_query(ledger_type, search)
    pagination = paginate(query, per_page=20)
    return render_template(
        "project/sheet_base.html",
        ledger_type=ledger_type,
        search=search,
        pagination=pagination,
        active_menu="file_management",
        active_submenu=view_name,
        breadcrumbs=_bc({"name": "文件管理", "url": url_for("project.import_file")}, {"name": page_title, "url": None}),
        page_title=page_title,
    )


@project_bp.route("/overview")
@login_required
def project_overview():
    """项目概况 — 项目列表页"""
    projects = _get_accessible_projects()
    return render_template(
        "project/overview.html",
        projects=projects,
        breadcrumbs=_bc({"name": "项目管理", "url": None}, {"name": "项目概况", "url": None}),
        page_title="项目概况",
    )


@project_bp.route("/model-sheet")
@login_required
def model_sheet():
    return _render_sheet("model_sheet")


@project_bp.route("/entry-sheet")
@login_required
def entry_sheet():
    return _render_sheet("entry_sheet")


@project_bp.route("/transfer-sheet")
@login_required
def transfer_sheet():
    return _render_sheet("transfer_sheet")


@project_bp.route("/waste-sheet")
@login_required
def waste_sheet():
    return _render_sheet("waste_sheet")


@project_bp.route("/remaining-sheet")
@login_required
def remaining_sheet():
    return _render_sheet("remaining_sheet")


@project_bp.route("/secondary-sheet")
@login_required
def secondary_sheet():
    return _render_sheet("secondary_sheet")


@project_bp.route("/detailing-sheet")
@login_required
def detailing_sheet():
    return _render_sheet("detailing_sheet")


@project_bp.route("/non-budget-sheet")
@login_required
def non_budget_sheet():
    return _render_sheet("non_budget_sheet")


@project_bp.route("/pile-foundation-sheet")
@login_required
def pile_foundation_sheet():
    return _render_sheet("pile_foundation_sheet")


@project_bp.route("/support-structure-sheet")
@login_required
def support_structure_sheet():
    return _render_sheet("support_structure_sheet")


@project_bp.route("/imported-files/<int:file_id>/download")
@login_required
def imported_file_download(file_id):
    """下载导入文件"""
    imported = ImportedFile.query.get_or_404(file_id)
    if not current_user.is_admin:
        accessible_ids = [p.id for p in _get_accessible_projects()]
        if imported.project_id not in accessible_ids:
            abort(403)
    directory = os.path.dirname(imported.file_path)
    filename = os.path.basename(imported.file_path)
    return send_from_directory(directory, filename, as_attachment=True, download_name=imported.original_filename)


@project_bp.route("/imported-files/<int:file_id>/delete", methods=["POST"])
@login_required
def imported_file_delete(file_id):
    """删除导入文件"""
    imported = ImportedFile.query.get_or_404(file_id)
    if not current_user.is_admin:
        accessible_ids = [p.id for p in _get_accessible_projects()]
        if imported.project_id not in accessible_ids:
            abort(403)
    try:
        if os.path.exists(imported.file_path):
            os.remove(imported.file_path)
        db.session.delete(imported)
        db.session.commit()
        flash("文件已删除。", "success")
    except Exception as e:
        flash(f"删除失败：{e}", "danger")
    return redirect(request.referrer or url_for("project.dashboard"))


LEDGER_TYPE_LABELS = {
    "incoming": "钢筋进场表",
    "transfer": "调拨钢筋表",
    "measure_rebar": "措施筋台账",
    "fangyang_requisition": "方样料单",
    "inventory": "钢筋剩余表",
    "waste": "废料钢筋表",
    "progress": "形象进度",
    "model_quantity": "钢筋模型表",
    "secondary": "钢筋二构表",
    "detailing": "钢筋翻样表",
    "non_budget": "非预算收入使用钢筋表",
    "pile_foundation": "主体桩基表",
    "support_structure": "基坑支护表",
}


SHEET_LEDGER_MAP = {
    "model_sheet": "model_quantity",
    "entry_sheet": "incoming",
    "transfer_sheet": "transfer",
    "waste_sheet": "waste",
    "remaining_sheet": "inventory",
    "secondary_sheet": "secondary",
    "detailing_sheet": "detailing",
    "non_budget_sheet": "non_budget",
    "pile_foundation_sheet": "pile_foundation",
    "support_structure_sheet": "support_structure",
}


def _get_accessible_projects():
    """获取当前用户可访问的项目"""
    if current_user.is_admin:
        return Project.query.order_by(Project.name).all()
    return Project.query.join(UserProject).filter(
        UserProject.user_id == current_user.id
    ).order_by(Project.name).all()


def _get_imported_files_query(ledger_type, search=None):
    """查询当前用户可访问的某类型导入文件"""
    query = ImportedFile.query.filter_by(ledger_type=ledger_type)
    if not current_user.is_admin:
        accessible_ids = [p.id for p in _get_accessible_projects()]
        if accessible_ids:
            query = query.filter(ImportedFile.project_id.in_(accessible_ids))
        else:
            query = query.filter(db.false())
    if search:
        query = query.filter(ImportedFile.original_filename.ilike(f"%{search}%"))
    return query.order_by(ImportedFile.uploaded_at.desc())


@project_bp.route("/import", methods=["GET", "POST"])
@login_required
def import_file():
    """项目文件导入页：上传 Excel 并保存到 imported_files"""
    ledger_type = request.args.get("type", "incoming")
    if ledger_type not in LEDGER_TYPE_LABELS:
        flash("不支持的台账类型。", "danger")
        return redirect(url_for("project.dashboard"))

    projects = _get_accessible_projects()

    if request.method == "POST":
        project_id = request.form.get("project_id", type=int)
        file = request.files.get("file")

        if not project_id:
            flash("请选择项目。", "warning")
            return redirect(url_for("project.import_file", type=ledger_type))
        if not file or not file.filename:
            flash("请选择文件。", "warning")
            return redirect(url_for("project.import_file", type=ledger_type))

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in (".xlsx", ".xls"):
            flash("仅支持 .xlsx/.xls 文件。", "danger")
            return redirect(url_for("project.import_file", type=ledger_type))

        try:
            project = Project.query.get_or_404(project_id)
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "imports", ledger_type)
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            # 避免覆盖：追加时间戳
            if os.path.exists(filepath):
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
                filepath = os.path.join(upload_dir, filename)
            file.save(filepath)

            imported = ImportedFile(
                project_id=project_id,
                ledger_type=ledger_type,
                original_filename=file.filename,
                file_path=filepath,
                file_size=os.path.getsize(filepath),
                uploaded_by=current_user.id,
            )
            db.session.add(imported)
            db.session.commit()
            flash(f"文件《{file.filename}》已上传并保存。", "success")
            return redirect(url_for("project.import_file", type=ledger_type))
        except Exception as e:
            flash(f"上传失败：{e}", "danger")
            return redirect(url_for("project.import_file", type=ledger_type))

    return render_template(
        "project/import.html",
        projects=projects,
        ledger_type=ledger_type,
        ledger_label=LEDGER_TYPE_LABELS.get(ledger_type, ledger_type),
        active_menu="file_management",
        active_submenu="import",
        breadcrumbs=_bc(
            {"name": "文件管理", "url": url_for("project.import_file")},
            {"name": "文件导入", "url": None},
        ),
        page_title=f"导入{LEDGER_TYPE_LABELS.get(ledger_type, ledger_type)}",
    )


# ========== 项目概况 ==========

@project_bp.route("/<int:project_id>/detail")
@login_required
@project_access_required
def detail(project_id):
    """项目详情页：5 Tab 聚合展示"""
    project = Project.query.get_or_404(project_id)

    # 当前激活的 Tab，默认概况
    active_tab = request.args.get("tab", "overview").strip()
    if active_tab not in ("overview", "members", "ledgers", "settlement", "profit"):
        active_tab = "overview"

    # Tab1 数据
    overview = get_project_overview(project_id)

    # Tab2 数据
    member_role = request.args.get("role", "").strip()
    member_search = request.args.get("search", "").strip()
    members = get_project_members(project_id, role=member_role or None, search=member_search or None)
    available_users = get_available_users(project_id)

    # Tab3 数据
    ledger_summary = get_ledger_summary(project_id)

    # Tab4 数据
    settlement = get_settlement_analysis(project_id)

    # Tab5 数据
    profit = get_profit_analysis(project_id)

    return render_template(
        "project/detail.html",
        project=project,
        active_tab=active_tab,
        overview=overview,
        members=members,
        member_role=member_role,
        member_search=member_search,
        available_users=available_users,
        member_role_map=MEMBER_ROLE_MAP,
        ledger_summary=ledger_summary,
        settlement=settlement,
        profit=profit,
        can_manage_members=_can_manage_members(project_id),
        current_project=project,
        active_menu="file_management",
        active_submenu="dashboard",
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": None},
        ),
        page_title=project.name,
    )


@project_bp.route("/<int:project_id>/detail/members/add", methods=["POST"])
@login_required
@project_access_required
def detail_member_add(project_id):
    """添加项目成员"""
    if not _can_manage_members(project_id):
        flash("您没有权限管理项目成员。", "danger")
        return redirect(url_for("project.detail", project_id=project_id, tab="members"))

    user_id = request.form.get("user_id", type=int)
    role = request.form.get("role", "engineer").strip()
    if not user_id:
        flash("请选择要添加的用户。", "warning")
        return redirect(url_for("project.detail", project_id=project_id, tab="members"))

    try:
        add_project_member(project_id, user_id, role=role)
        flash("成员添加成功。", "success")
    except Exception as e:
        flash(f"添加失败: {e}", "danger")

    return redirect(url_for("project.detail", project_id=project_id, tab="members"))


@project_bp.route("/<int:project_id>/detail/members/<int:user_id>/remove", methods=["POST"])
@login_required
@project_access_required
def detail_member_remove(project_id, user_id):
    """移除项目成员"""
    if not _can_manage_members(project_id):
        flash("您没有权限管理项目成员。", "danger")
        return redirect(url_for("project.detail", project_id=project_id, tab="members"))

    try:
        remove_project_member(project_id, user_id)
        flash("成员已移除。", "success")
    except Exception as e:
        flash(f"移除失败: {e}", "danger")

    return redirect(url_for("project.detail", project_id=project_id, tab="members"))


@project_bp.route("/<int:project_id>/detail/settlement/export")
@login_required
@project_access_required
def settlement_export(project_id):
    """导出项目结算分析 Excel"""
    from flask import send_file

    output_dir = os.path.join(current_app.config["EXPORT_FOLDER"], "settlements")
    filepath = export_settlement_analysis(project_id, output_dir)
    return send_file(filepath, as_attachment=True)


@project_bp.route("/<int:project_id>/attachments")
@login_required
@project_access_required
def attachments(project_id):
    project = Project.query.get_or_404(project_id)
    atts = get_project_attachments(project_id)
    return render_template(
        "project/attachments/manage.html",
        project=project,
        attachments=atts,
        current_project=project,
        active_menu="file_management",
        active_submenu="attachments",
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "模型效果图", "url": None},
        ),
        page_title="模型效果图",
    )

@project_bp.route("/<int:project_id>/attachments/upload", methods=["POST"])
@login_required
@project_access_required
def attachment_upload(project_id):
    if "file" not in request.files:
        flash("请选择文件。", "warning")
        return redirect(url_for("project.attachments", project_id=project_id))
    file = request.files["file"]
    if not file.filename or not validate_image(file.filename, file.content_type):
        flash("不支持的文件格式。", "danger")
        return redirect(url_for("project.attachments", project_id=project_id))
    try:
        save_attachment(project_id, file, request.form.get("description", ""), current_user.id)
        flash("上传成功。", "success")
    except Exception as e:
        flash(f"上传失败: {e}", "danger")
    return redirect(url_for("project.attachments", project_id=project_id))

@project_bp.route("/<int:project_id>/attachments/<int:att_id>/delete", methods=["POST"])
@login_required
@project_access_required
def attachment_delete(project_id, att_id):
    att = ProjectAttachment.query.get_or_404(att_id)
    if att.project_id != int(project_id):
        flash("无权操作。", "danger")
        return redirect(url_for("project.attachments", project_id=project_id))
    delete_attachment(att_id)
    flash("已删除。", "success")
    return redirect(url_for("project.attachments", project_id=project_id))

@project_bp.route("/<int:project_id>/attachments/<int:att_id>/cover", methods=["POST"])
@login_required
@project_access_required
def attachment_set_cover(project_id, att_id):
    att = ProjectAttachment.query.get_or_404(att_id)
    if att.project_id != int(project_id):
        flash("无权操作。", "danger")
        return redirect(url_for("project.attachments", project_id=project_id))
    set_cover(att_id)
    flash("封面已设置。", "success")
    return redirect(url_for("project.attachments", project_id=project_id))

@project_bp.route("/<int:project_id>/attachments/<int:att_id>/file")
@login_required
@project_access_required
def attachment_file(project_id, att_id):
    att = ProjectAttachment.query.get_or_404(att_id)
    if att.project_id != int(project_id):
        return "Forbidden", 403
    directory = os.path.join(current_app.config["UPLOAD_FOLDER"], "attachments", str(project_id))
    return send_from_directory(directory, os.path.basename(att.file_path))


# ========== 料单台账 ==========

@project_bp.route("/<int:project_id>/cutting-orders")
@login_required
@project_access_required
def cutting_order_list(project_id):
    project = Project.query.get_or_404(project_id)
    query = get_project_orders(project_id)
    pagination = paginate(query, per_page=20)
    return render_template(
        "project/cutting_orders/list.html",
        project=project,
        pagination=pagination,
        current_project=project,
        active_menu="audit",
        active_submenu="cutting_orders",
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "料单台账", "url": None},
        ),
        page_title="料单台账",
    )

@project_bp.route("/<int:project_id>/cutting-orders/create", methods=["GET", "POST"])
@login_required
@project_access_required
def cutting_order_create(project_id):
    project = Project.query.get_or_404(project_id)
    if request.method == "POST":
        try:
            order = create_order(
                project_id=project_id,
                order_date=request.form["order_date"],
                batch_no=request.form.get("batch_no"),
                labor_team=request.form.get("labor_team"),
                use_location=request.form.get("use_location"),
                created_by=current_user.id,
            )
            flash("料单创建成功。", "success")
            return redirect(url_for("project.cutting_order_detail", project_id=project_id, order_id=order.id))
        except Exception as e:
            flash(f"创建失败: {e}", "danger")
    return render_template(
        "project/cutting_orders/form.html",
        project=project,
        order=None,
        current_project=project,
        active_menu="audit",
        active_submenu="cutting_orders",
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "料单台账", "url": url_for("project.cutting_order_list", project_id=project.id)},
            {"name": "创建料单", "url": None},
        ),
        page_title="创建料单",
    )

@project_bp.route("/<int:project_id>/cutting-orders/<int:order_id>")
@login_required
@project_access_required
def cutting_order_detail(project_id, order_id):
    project = Project.query.get_or_404(project_id)
    order = get_order_by_id(order_id)
    items = get_order_items(order_id)
    return render_template(
        "project/cutting_orders/detail.html",
        project=project,
        order=order,
        items=items,
        current_project=project,
        active_menu="audit",
        active_submenu="cutting_orders",
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "料单台账", "url": url_for("project.cutting_order_list", project_id=project.id)},
            {"name": "料单详情", "url": None},
        ),
        page_title="料单详情",
    )

@project_bp.route("/<int:project_id>/cutting-orders/<int:order_id>/add-item", methods=["POST"])
@login_required
@project_access_required
def cutting_order_add_item(project_id, order_id):
    try:
        items = get_order_items(order_id)
        add_order_item(
            order_id=order_id,
            line_no=len(items) + 1,
            spec=request.form.get("spec", ""),
            rebar_diameter=request.form.get("rebar_diameter"),
            cut_length=request.form.get("cut_length", type=float),
            piece_count=request.form.get("piece_count", type=int),
            unit_weight=request.form.get("unit_weight", type=float),
            rebar_shape=request.form.get("rebar_shape"),
            component_name=request.form.get("component_name"),
        )
        flash("明细已添加。", "success")
    except Exception as e:
        flash(f"添加失败: {e}", "danger")
    return redirect(url_for("project.cutting_order_detail", project_id=project_id, order_id=order_id))

@project_bp.route("/<int:project_id>/cutting-orders/<int:order_id>/delete-item/<int:item_id>", methods=["POST"])
@login_required
@project_access_required
def cutting_order_delete_item(project_id, order_id, item_id):
    try:
        delete_order_item(item_id)
        flash("明细已删除。", "success")
    except Exception as e:
        flash(f"删除失败: {e}", "danger")
    return redirect(url_for("project.cutting_order_detail", project_id=project_id, order_id=order_id))

@project_bp.route("/<int:project_id>/cutting-orders/<int:order_id>/submit", methods=["POST"])
@login_required
@project_access_required
def cutting_order_submit(project_id, order_id):
    try:
        submit_order(order_id, current_user.id)
        flash("料单已提交审核。", "success")
    except Exception as e:
        flash(f"提交失败: {e}", "danger")
    return redirect(url_for("project.cutting_order_detail", project_id=project_id, order_id=order_id))

@project_bp.route("/<int:project_id>/cutting-orders/<int:order_id>/delete", methods=["POST"])
@login_required
@project_access_required
def cutting_order_delete(project_id, order_id):
    try:
        delete_order(order_id)
        flash("料单已删除。", "success")
    except Exception as e:
        flash(f"删除失败: {e}", "danger")
    return redirect(url_for("project.cutting_order_list", project_id=project_id))


# ========== 项目成本 ==========

@project_bp.route("/<int:project_id>/costs")
@login_required
@project_access_required
def cost_list(project_id):
    project = Project.query.get_or_404(project_id)
    costs = get_project_costs(project_id)
    summary = get_cost_summary(project_id)
    return render_template(
        "project/costs/list.html",
        project=project,
        costs=costs,
        summary=summary,
        CATEGORY_LABELS=CATEGORY_LABELS,
        current_project=project,
        active_menu="audit",
        active_submenu="costs",
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "项目成本", "url": None},
        ),
        page_title="项目成本",
    )

@project_bp.route("/<int:project_id>/costs/create", methods=["GET", "POST"])
@login_required
@project_access_required
def cost_create(project_id):
    project = Project.query.get_or_404(project_id)
    if request.method == "POST":
        try:
            create_cost(
                project_id=project_id,
                cost_date=request.form["cost_date"],
                cost_category=request.form["cost_category"],
                cost_item=request.form["cost_item"],
                amount=float(request.form["amount"]),
                description=request.form.get("description"),
                receipt_no=request.form.get("receipt_no"),
                created_by=current_user.id,
            )
            flash("成本已录入。", "success")
            return redirect(url_for("project.cost_list", project_id=project_id))
        except Exception as e:
            flash(f"录入失败: {e}", "danger")
    return render_template(
        "project/costs/form.html",
        project=project,
        cost=None,
        CATEGORY_LABELS=CATEGORY_LABELS,
        current_project=project,
        active_menu="audit",
        active_submenu="costs",
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "项目成本", "url": url_for("project.cost_list", project_id=project.id)},
            {"name": "录入成本", "url": None},
        ),
        page_title="录入成本",
    )

@project_bp.route("/<int:project_id>/costs/<int:cost_id>/edit", methods=["GET", "POST"])
@login_required
@project_access_required
def cost_edit(project_id, cost_id):
    project = Project.query.get_or_404(project_id)
    cost = get_cost_by_id(cost_id)
    if request.method == "POST":
        try:
            update_cost(cost_id, **{
                "cost_date": request.form["cost_date"],
                "cost_category": request.form["cost_category"],
                "cost_item": request.form["cost_item"],
                "amount": request.form["amount"],
                "description": request.form.get("description"),
                "receipt_no": request.form.get("receipt_no"),
            })
            flash("成本已更新。", "success")
            return redirect(url_for("project.cost_list", project_id=project_id))
        except Exception as e:
            flash(f"更新失败: {e}", "danger")
    return render_template(
        "project/costs/form.html",
        project=project,
        cost=cost,
        CATEGORY_LABELS=CATEGORY_LABELS,
        current_project=project,
        active_menu="audit",
        active_submenu="costs",
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "项目成本", "url": url_for("project.cost_list", project_id=project.id)},
            {"name": "编辑成本", "url": None},
        ),
        page_title="编辑成本",
    )

@project_bp.route("/<int:project_id>/costs/<int:cost_id>/delete", methods=["POST"])
@login_required
@project_access_required
def cost_delete(project_id, cost_id):
    try:
        delete_cost(cost_id)
        flash("成本已删除。", "success")
    except Exception as e:
        flash(f"删除失败: {e}", "danger")
    return redirect(url_for("project.cost_list", project_id=project_id))


# ========== 项目盈亏 ==========

@project_bp.route("/<int:project_id>/pl-analysis")
@login_required
@project_access_required
def pl_analysis(project_id):
    project = Project.query.get_or_404(project_id)
    pl = get_project_pl(project_id)
    costs = get_project_costs(project_id)
    summary = get_cost_summary(project_id)
    return render_template(
        "project/pl_analysis/dashboard.html",
        project=project,
        pl=pl,
        costs=costs,
        summary=summary,
        current_project=project,
        active_menu="audit",
        active_submenu="pl_analysis",
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "项目盈亏", "url": None},
        ),
        page_title="项目盈亏",
    )

@project_bp.route("/<int:project_id>/pl-analysis/update-price", methods=["POST"])
@login_required
@project_access_required
def pl_update_price(project_id):
    try:
        update_unit_price(project_id, float(request.form["unit_price"]))
        flash(f"定价已更新。", "success")
    except Exception as e:
        flash(f"更新失败: {e}", "danger")
    return redirect(url_for("project.pl_analysis", project_id=project_id))

@project_bp.route("/<int:project_id>/pl-analysis/update-other-income", methods=["POST"])
@login_required
@project_access_required
def pl_update_other_income(project_id):
    try:
        update_other_income(project_id, float(request.form["other_income"]))
        flash(f"其他收入已更新。", "success")
    except Exception as e:
        flash(f"更新失败: {e}", "danger")
    return redirect(url_for("project.pl_analysis", project_id=project_id))


# ============================================
# 项目数据看板
# ============================================

@project_bp.route("/<int:project_id>/dashboard")
@login_required
@project_access_required
def dashboard_project(project_id):
    """项目级数据看板：复用项目详情页"""
    return redirect(url_for("project.detail", project_id=project_id))


# ============================================
# 文件管理（包装 ledger / bom 视图，统一 active_menu）
# ============================================

@project_bp.route("/<int:project_id>/files/incoming")
@login_required
@project_access_required
def file_incoming(project_id):
    """进场台账"""
    from app.routes.ledger import incoming_list
    return incoming_list(project_id, active_menu="file_management", active_submenu="incoming")


@project_bp.route("/<int:project_id>/files/transfer")
@login_required
@project_access_required
def file_transfer(project_id):
    """调拨台账"""
    from app.routes.ledger import transfer_list
    return transfer_list(project_id, active_menu="file_management", active_submenu="transfer")


@project_bp.route("/<int:project_id>/files/measure_rebar")
@login_required
@project_access_required
def file_measure(project_id):
    """措施筋台账"""
    from app.routes.ledger import measure_list
    return measure_list(project_id, active_menu="file_management", active_submenu="measure")


@project_bp.route("/<int:project_id>/files/inventory")
@login_required
@project_access_required
def file_inventory(project_id):
    """盘点表"""
    from app.routes.ledger import inventory_list
    return inventory_list(project_id, active_menu="file_management", active_submenu="inventory")


@project_bp.route("/<int:project_id>/files/waste")
@login_required
@project_access_required
def file_waste(project_id):
    """废料台账"""
    from app.routes.ledger import waste_list
    return waste_list(project_id, active_menu="file_management", active_submenu="waste")


@project_bp.route("/<int:project_id>/files/progress")
@login_required
@project_access_required
def file_progress(project_id):
    """形象进度"""
    from app.routes.ledger import progress_view
    return progress_view(project_id, active_menu="file_management", active_submenu="progress")


@project_bp.route("/<int:project_id>/files/model_quantity")
@login_required
@project_access_required
def file_model(project_id):
    """模型量：复用方样料单数据汇总"""
    from app.routes.bom import summary
    return summary(project_id, active_menu="file_management", active_submenu="model_quantity")


@project_bp.route("/<int:project_id>/import")
@login_required
@project_access_required
def file_import(project_id):
    """文件导入入口：默认进入进场台账导入"""
    from app.routes.ledger import import_data
    return import_data(project_id, "incoming", active_menu="file_management", active_submenu="import")
