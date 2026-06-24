# ============================================
# 钢筋精细化管理平台 — 承接公司/甲件/项目 CRUD 服务
# ============================================
from app import db
from app.models import Contractor, ClientUnit, Project
from app.models.audit import OperationLog
from flask_login import current_user
from flask import request
from sqlalchemy.orm import joinedload


def log_op(action: str, target: str):
    """记录操作日志"""
    try:
        db.session.add(
            OperationLog(
                user_id=current_user.id,
                action=action,
                target=target,
                ip_address=request.remote_addr,
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()


# ===== 承接公司 =====

def get_all_contractors():
    return Contractor.query.order_by(Contractor.name).all()


def get_contractor_by_id(contractor_id):
    return Contractor.query.get_or_404(contractor_id)


def create_contractor(name, contact_person=None, contact_phone=None, address=None, remark=None):
    c = Contractor(
        name=name,
        contact_person=contact_person,
        contact_phone=contact_phone,
        address=address,
        remark=remark,
    )
    db.session.add(c)
    db.session.commit()
    log_op("create_contractor", f"承接公司: {name}")
    return c


def update_contractor(contractor_id, **kwargs):
    c = get_contractor_by_id(contractor_id)
    for key in ["name", "contact_person", "contact_phone", "address", "remark"]:
        if key in kwargs and kwargs[key] is not None:
            setattr(c, key, kwargs[key])
    db.session.commit()
    log_op("update_contractor", f"承接公司: {c.name}")
    return c


def delete_contractor(contractor_id):
    c = get_contractor_by_id(contractor_id)
    name = c.name
    db.session.delete(c)
    db.session.commit()
    log_op("delete_contractor", f"承接公司: {name}")


# ===== 甲件单位 =====

def get_all_client_units():
    return ClientUnit.query.order_by(ClientUnit.name).all()


def get_client_unit_by_id(unit_id):
    return ClientUnit.query.get_or_404(unit_id)


def create_client_unit(name):
    cu = ClientUnit(name=name)
    db.session.add(cu)
    db.session.commit()
    log_op("create_client_unit", f"甲方单位: {name}")
    return cu


def update_client_unit(unit_id, name):
    cu = get_client_unit_by_id(unit_id)
    cu.name = name
    db.session.commit()
    log_op("update_client_unit", f"甲方单位: {name}")
    return cu


def delete_client_unit(unit_id):
    cu = get_client_unit_by_id(unit_id)
    name = cu.name
    db.session.delete(cu)
    db.session.commit()
    log_op("delete_client_unit", f"甲方单位: {name}")


# ===== 项目 =====

def get_all_projects():
    return (
        Project.query
        .options(
            joinedload(Project.client_unit),
            joinedload(Project.contractor),
        )
        .order_by(Project.updated_at.desc())
        .all()
    )


def get_project_by_id(project_id):
    return Project.query.options(
        joinedload(Project.client_unit),
        joinedload(Project.contractor),
    ).get_or_404(project_id)


def create_project(
    name,
    client_unit_id=None,
    contractor_id=None,
    description=None,
    contract_name=None,
    contract_no=None,
    project_name=None,
    total_contractor_name=None,
    start_date=None,
    duration_days=None,
    est_rebar_total=None,
    building_area=None,
    rebar_content=None,
    project_location=None,
    service_scope=None,
    service_content=None,
    service_duration=None,
):
    p = Project(
        name=name,
        contract_name=contract_name,
        contract_no=contract_no,
        project_name=project_name,
        total_contractor_name=total_contractor_name,
        client_unit_id=client_unit_id if client_unit_id else None,
        contractor_id=contractor_id if contractor_id else None,
        description=description,
        start_date=start_date,
        duration_days=duration_days,
        est_rebar_total=est_rebar_total,
        building_area=building_area,
        rebar_content=rebar_content,
        project_location=project_location,
        service_scope=service_scope,
        service_content=service_content,
        service_duration=service_duration,
    )
    db.session.add(p)
    db.session.commit()
    log_op("create_project", f"项目: {name}")
    return p


def update_project(project_id, **kwargs):
    p = get_project_by_id(project_id)
    for key in [
        "name", "contract_name", "contract_no", "project_name", "total_contractor_name",
        "client_unit_id", "contractor_id", "description",
        "status", "start_date", "duration_days", "est_rebar_total",
        "building_area", "rebar_content", "project_location",
        "service_scope", "service_content", "service_duration",
    ]:
        if key in kwargs and kwargs[key] is not None:
            if key.endswith("_id") and kwargs[key] == 0:
                setattr(p, key, None)
            else:
                setattr(p, key, kwargs[key])
    db.session.commit()
    log_op("update_project", f"项目: {p.name}")
    return p


def delete_project(project_id):
    p = get_project_by_id(project_id)
    name = p.name
    db.session.delete(p)
    db.session.commit()
    log_op("delete_project", f"项目: {name}")
