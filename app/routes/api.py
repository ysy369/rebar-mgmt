# ============================================
# 钢筋精细化管理平台 — JSON API 蓝图
# ============================================
from flask import Blueprint, jsonify
from flask_login import login_required

from app import db
from app.models import ClientUnit, Contractor, Project, ImportedFile
from app.celery_app import celery

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/projects/by-client/<int:client_id>")
@login_required
def projects_by_client(client_id):
    """获取某甲方下的所有活跃项目（级联下拉）"""
    projects = (
        Project.query
        .filter_by(client_unit_id=client_id, status="in_progress")
        .order_by(Project.name)
        .all()
    )
    return jsonify([{"id": p.id, "name": p.name} for p in projects])


@api_bp.route("/projects/by-contractor/<int:contractor_id>")
@login_required
def projects_by_contractor(contractor_id):
    """获取某承接公司下的所有活跃项目"""
    projects = (
        Project.query
        .filter_by(contractor_id=contractor_id, status="in_progress")
        .order_by(Project.name)
        .all()
    )
    return jsonify([{"id": p.id, "name": p.name} for p in projects])


@api_bp.route("/clients")
@login_required
def all_clients():
    """所有甲方单位"""
    units = ClientUnit.query.order_by(ClientUnit.name).all()
    return jsonify([{"id": u.id, "name": u.name} for u in units])


@api_bp.route("/contractors")
@login_required
def all_contractors():
    """所有承接公司"""
    contractors = Contractor.query.order_by(Contractor.name).all()
    return jsonify([{"id": c.id, "name": c.name} for c in contractors])


@api_bp.route("/task/<task_id>/status")
@login_required
def task_status(task_id):
    """查询 Celery 异步导入任务状态 + 数据库进度"""
    task = celery.AsyncResult(task_id)
    imported_file = ImportedFile.query.filter_by(task_id=task_id).first()

    response = {
        "task_id": task_id,
        "celery_status": task.status,
    }

    if imported_file:
        response.update({
            "status": imported_file.status,
            "progress": imported_file.progress,
            "filename": imported_file.original_filename,
            "error_message": imported_file.error_message,
        })

    # 同步 Celery 最终状态到数据库
    if task.ready() and imported_file and imported_file.status in ["pending", "processing"]:
        if task.successful():
            imported_file.status = "completed"
            imported_file.progress = 100
        else:
            imported_file.status = "failed"
            result = task.result
            if isinstance(result, Exception):
                imported_file.error_message = str(result)
            elif isinstance(result, dict):
                imported_file.error_message = result.get("error", "未知错误")
            else:
                imported_file.error_message = str(result) if result else "未知错误"
        db.session.commit()
        response["status"] = imported_file.status

    return jsonify(response)
