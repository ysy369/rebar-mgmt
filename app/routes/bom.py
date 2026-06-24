# ============================================
# 钢筋精细化管理平台 — 配料单(BOM)管理蓝图
# ============================================
from datetime import datetime as dt_datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import Project
from app.models.bom import Component, RebarDetail, ImportBatch
from app.services.pagination_service import paginate
from app.services.bom_import import process_upload_batch
from app.services.bom_service import (
    get_project_tree, get_components_by_filter, get_component_detail,
    update_component_status, batch_update_status, get_status_summary,
    get_diameter_summary, get_import_batches, delete_batch,
)

bom_bp = Blueprint("bom", __name__, template_folder="../templates/bom")


def _bc(*items):
    """构造统一面包屑：首页 + 各级节点"""
    base = [{"name": "钢筋管理平台", "url": url_for("dashboard.index")}]
    base.extend(items)
    return base


@bom_bp.route("/dashboard")
@login_required
def dashboard():
    """配料单模块首页"""
    if current_user.is_admin:
        projects = Project.query.filter_by(status="in_progress").order_by(Project.name).all()
    else:
        from app.models import UserProject
        projects = Project.query.join(UserProject).filter(
            UserProject.user_id == current_user.id, Project.status == "active"
        ).order_by(Project.name).all()
    return render_template(
        "bom/dashboard.html",
        projects=projects,
        breadcrumbs=_bc({"name": "方样料单", "url": None}, {"name": "项目列表", "url": None}),
        page_title="方样料单项目",
    )


def _check_bom_project_access(project_id):
    """检查用户是否有权访问该项目的BOM数据"""
    from app.services.auth_service import can_access_project
    if not can_access_project(current_user.id, int(project_id)):
        from flask import abort
        abort(403)


@bom_bp.route("/<int:project_id>/import", methods=["GET", "POST"])
@login_required
def import_page(project_id, active_menu="file_management", active_submenu="import"):
    """批量导入页面"""
    _check_bom_project_access(project_id)
    project = Project.query.get_or_404(project_id)
    if request.method == "POST":
        files = request.files.getlist("files")
        if not files or not any(f.filename for f in files):
            flash("请选择要上传的文件。", "warning")
            return redirect(url_for("bom.import_page", project_id=project_id))
        try:
            result = process_upload_batch(project_id, files, current_user.id)
            flash(f"导入完成：成功 {result['success']} 条，失败 {result['failed']} 条。", "success")
            if result["errors"]:
                for err in result["errors"][:5]:
                    flash(err, "warning")
        except Exception as e:
            flash(f"导入失败：{e}", "danger")
        return redirect(url_for("bom.import_page", project_id=project_id))

    batches = get_import_batches(project_id)
    return render_template(
        "bom/import.html",
        project=project,
        batches=batches,
        current_project=project,
        active_menu=active_menu,
        active_submenu=active_submenu,
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "方样料单", "url": url_for("bom.summary", project_id=project.id)},
            {"name": "配料单导入", "url": None},
        ),
        page_title="方样料单导入",
    )


@bom_bp.route("/<int:project_id>/summary")
@login_required
def summary(project_id, active_menu="file_management", active_submenu="summary"):
    """数据汇总展示"""
    _check_bom_project_access(project_id)
    project = Project.query.get_or_404(project_id)
    tree = get_project_tree(project_id)
    status_summary = get_status_summary(project_id=project_id)
    dia_summary = get_diameter_summary(project_id=project_id)

    # 筛选参数
    filters = {
        "building_id": request.args.get("building_id", "all"),
        "floor_id": request.args.get("floor_id", "all"),
        "area_id": request.args.get("area_id", "all"),
        "component_types": request.args.getlist("component_type"),
        "statuses": request.args.getlist("status"),
    }
    components_query = get_components_by_filter(
        project_id=project_id,
        building_id=filters["building_id"],
        floor_id=filters["floor_id"],
        area_id=filters["area_id"],
        component_types=filters["component_types"] or None,
        statuses=filters["statuses"] or None,
    )
    components_pagination = paginate(components_query.order_by(Component.name), per_page=50)
    components = components_pagination.items

    # 图表数据基于全部筛选结果，不受分页影响
    all_components = components_query.all()
    type_summary = {}
    for comp in all_components:
        t = comp.component_type
        type_summary[t] = round(type_summary.get(t, 0) + comp.total_weight, 3)

    # 按楼层汇总
    floor_summary = {}
    for b in tree:
        for f_node in b.get("children", []):
            fw = 0
            fname = f_node["name"]
            for a_node in f_node.get("children", []):
                for c_node in a_node.get("children", []):
                    comp = next((x for x in all_components if x.id == c_node["id"]), None)
                    if comp:
                        fw += comp.total_weight
            if fw > 0:
                floor_summary[fname] = round(fw, 3)

    import json
    return render_template(
        "bom/summary.html",
        project=project, tree=tree, components=components,
        components_pagination=components_pagination,
        status_summary=status_summary, dia_summary=dia_summary, filters=filters,
        type_summary=type_summary, floor_summary=floor_summary,
        type_summary_json=json.dumps(type_summary, ensure_ascii=False),
        floor_summary_json=json.dumps(floor_summary, ensure_ascii=False),
        current_project=project,
        active_menu=active_menu,
        active_submenu=active_submenu,
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "方样料单", "url": None},
            {"name": "数据汇总", "url": None},
        ),
        page_title="数据汇总",
    )


@bom_bp.route("/<int:project_id>/component/<int:comp_id>")
@login_required
def component_detail(project_id, comp_id, active_menu="file_management", active_submenu="summary"):
    """构件明细"""
    _check_bom_project_access(project_id)
    project = Project.query.get_or_404(project_id)
    comp, details = get_component_detail(comp_id)
    return render_template(
        "bom/component_detail.html",
        project=project,
        comp=comp,
        details=details,
        current_project=project,
        active_menu=active_menu,
        active_submenu=active_submenu,
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "方样料单", "url": url_for("bom.summary", project_id=project.id)},
            {"name": "数据汇总", "url": url_for("bom.summary", project_id=project.id)},
            {"name": "构件明细", "url": None},
        ),
        page_title=comp.name if comp else "构件明细",
    )


@bom_bp.route("/<int:project_id>/component/<int:comp_id>/status", methods=["POST"])
@login_required
def update_status(project_id, comp_id):
    """更新施工状态"""
    new_status = request.form.get("status")
    try:
        update_component_status(comp_id, new_status)
        flash("状态已更新。", "success")
    except Exception as e:
        flash(f"更新失败: {e}", "danger")
    return redirect(url_for("bom.summary", project_id=project_id))


@bom_bp.route("/<int:project_id>/batch-status", methods=["POST"])
@login_required
def batch_status(project_id):
    """批量更新状态"""
    ids = request.form.getlist("comp_ids")
    new_status = request.form.get("status")
    if ids and new_status:
        count = batch_update_status([int(i) for i in ids], new_status)
        flash(f"已更新 {count} 个构件的状态为「{new_status}」。", "success")
    return redirect(url_for("bom.summary", project_id=project_id))


@bom_bp.route("/<int:project_id>/export")
@login_required
def export_summary(project_id):
    """导出 Excel"""
    _check_bom_project_access(project_id)
    import os
    from flask import send_file, current_app
    from app.services.bom_export import export_project_summary

    export_dir = os.path.join(current_app.config["EXPORT_FOLDER"], "bom")
    os.makedirs(export_dir, exist_ok=True)
    try:
        filepath = export_project_summary(project_id, export_dir)
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
    except Exception as e:
        flash(f"导出失败: {e}", "danger")
        return redirect(url_for("bom.summary", project_id=project_id))


@bom_bp.route("/<int:project_id>/component/<int:comp_id>/edit-weight", methods=["POST"])
@login_required
def edit_weight(project_id, comp_id):
    """编辑钢筋重量"""
    detail_id = request.form.get("detail_id", type=int)
    new_weight = request.form.get("weight", type=float)
    if detail_id and new_weight is not None:
        detail = RebarDetail.query.get_or_404(detail_id)
        detail.weight = new_weight
        from app import db
        db.session.commit()
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "参数错误"}), 400


@bom_bp.route("/<int:project_id>/batch/<int:batch_id>/delete", methods=["POST"])
@login_required
def delete_import_batch(project_id, batch_id):
    """删除导入批次"""
    try:
        delete_batch(batch_id)
        flash("批次已删除。", "success")
    except Exception as e:
        flash(f"删除失败: {e}", "danger")
    return redirect(url_for("bom.import_page", project_id=project_id))


# ===== JSON API =====

@bom_bp.route("/<int:project_id>/batch/<int:batch_id>/download")
@login_required
def download_source(project_id, batch_id):
    """下载导入批次源文件"""
    import os
    from flask import send_file
    batch = ImportBatch.query.get_or_404(batch_id)
    if batch.source_path:
        paths = batch.source_path.split(",")
        if len(paths) == 1 and os.path.exists(paths[0]):
            return send_file(paths[0], as_attachment=True, download_name=os.path.basename(paths[0]))
    flash("源文件不存在。", "warning")
    return redirect(url_for("bom.import_page", project_id=project_id))


# ===== 管理员审核 =====

@bom_bp.route("/admin/review")
@login_required
def admin_review_list():
    """管理员审核配料单批次"""
    from app.services.auth_service import admin_required as admin_req
    if not current_user.is_admin:
        from flask import abort
        abort(403)

    status = request.args.get("status")
    query = ImportBatch.query
    if status:
        query = query.filter_by(status=status)
    batches = query.order_by(ImportBatch.created_at.desc()).limit(50).all()
    return render_template(
        "bom/admin_review.html",
        batches=batches,
        current_status=status,
        breadcrumbs=_bc({"name": "方样料单", "url": None}, {"name": "批次审核", "url": None}),
        page_title="批次审核",
    )


@bom_bp.route("/<int:project_id>/admin/review")
@login_required
def project_review_list(project_id, active_menu="audit", active_submenu="batch_review"):
    """项目上下文下的批次审核"""
    if not current_user.is_admin:
        from flask import abort
        abort(403)
    _check_bom_project_access(project_id)
    project = Project.query.get_or_404(project_id)
    status = request.args.get("status")
    query = ImportBatch.query.filter_by(project_id=project_id)
    if status:
        query = query.filter_by(status=status)
    batches = query.order_by(ImportBatch.created_at.desc()).limit(50).all()
    return render_template(
        "bom/admin_review.html",
        batches=batches,
        current_status=status,
        current_project=project,
        active_menu=active_menu,
        active_submenu=active_submenu,
        breadcrumbs=_bc(
            {"name": "项目管理", "url": url_for("admin.project_list")},
            {"name": project.name, "url": url_for("project.detail", project_id=project.id)},
            {"name": "方样料单", "url": url_for("bom.summary", project_id=project.id)},
            {"name": "批次审核", "url": None},
        ),
        page_title="批次审核",
    )


@bom_bp.route("/admin/review/<int:batch_id>", methods=["POST"])
@login_required
def admin_review_action(batch_id):
    """审核操作"""
    if not current_user.is_admin:
        from flask import abort
        abort(403)

    action = request.form.get("action")
    comment = request.form.get("comment", "")
    batch = ImportBatch.query.get_or_404(batch_id)

    try:
        if action == "approved":
            batch.status = "approved"
            batch.reviewed_by = current_user.id
            batch.reviewed_at = dt_datetime.utcnow()
            batch.review_comment = comment
            flash("批次审核通过。", "success")
        elif action == "rejected":
            batch.status = "rejected"
            batch.reviewed_by = current_user.id
            batch.reviewed_at = dt_datetime.utcnow()
            batch.review_comment = comment
            flash("批次已驳回。", "warning")
        else:
            flash("无效操作。", "danger")
        from app import db
        db.session.commit()
    except Exception as e:
        flash(f"操作失败: {e}", "danger")
        from app import db
        db.session.rollback()

    return redirect(url_for("bom.project_review_list", project_id=batch.project_id) if batch.project_id else url_for("bom.admin_review_list"))


@bom_bp.route("/<int:project_id>/api/tree")
@login_required
def api_tree(project_id):
    """获取项目树 JSON"""
    tree = get_project_tree(project_id)
    return jsonify(tree)


@bom_bp.route("/<int:project_id>/api/status-summary")
@login_required
def api_status_summary(project_id):
    """获取状态统计 JSON"""
    building_id = request.args.get("building_id", "all")
    floor_id = request.args.get("floor_id", "all")
    area_id = request.args.get("area_id", "all")
    summary = get_status_summary(project_id, building_id, floor_id, area_id)
    return jsonify(summary)
