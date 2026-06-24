# ============================================
# 钢筋精细化管理平台 — JSON API 蓝图
# ============================================
from flask import Blueprint, jsonify
from flask_login import login_required

from app.models import ClientUnit, Contractor, Project

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
