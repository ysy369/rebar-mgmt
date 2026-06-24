# ============================================
# 配料单数据服务
# ============================================
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.models.bom import Building, Floor, Area, Component, RebarDetail, ImportBatch

DIAMETER_COLS = [6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 32]


def get_project_tree(project_id: int):
    """获取项目完整树形结构（使用 joinedload 避免 N+1）"""
    buildings = (
        Building.query.filter_by(project_id=project_id)
        .options(
            joinedload(Building.floors).joinedload(Floor.areas).joinedload(Area.components)
        )
        .order_by(Building.name)
        .all()
    )
    tree = []
    for b in buildings:
        b_data = {"id": b.id, "name": b.name, "type": "building", "children": []}
        floors = sorted(b.floors, key=lambda f: (f.sort_order, f.name))
        for f in floors:
            f_data = {"id": f.id, "name": f.name, "type": "floor", "building_id": b.id, "children": []}
            areas = sorted(f.areas, key=lambda a: a.name)
            for a in areas:
                a_data = {"id": a.id, "name": a.name, "type": "area", "floor_id": f.id, "children": []}
                comps = sorted(a.components, key=lambda c: c.name)
                for c in comps:
                    a_data["children"].append({
                        "id": c.id, "name": c.name, "type": "component",
                        "component_type": c.component_type, "status": c.status,
                        "area_id": a.id,
                    })
                f_data["children"].append(a_data)
            b_data["children"].append(f_data)
        tree.append(b_data)
    return tree


def get_components_by_filter(project_id: int = None, building_id: str = None,
                             floor_id: str = None, area_id: str = None,
                             component_types: list = None, statuses: list = None):
    """按筛选条件获取构件列表（分页）"""
    query = Component.query.join(Area).join(Floor).join(Building)

    if building_id and building_id != "all":
        query = query.filter(Building.id == int(building_id))
    if floor_id and floor_id != "all":
        query = query.filter(Floor.id == int(floor_id))
    if area_id and area_id != "all":
        query = query.filter(Area.id == int(area_id))
    if project_id:
        query = query.filter(Building.project_id == project_id)
    if component_types:
        query = query.filter(Component.component_type.in_(component_types))
    if statuses:
        query = query.filter(Component.status.in_(statuses))

    return query.order_by(Component.name).all()


def get_component_detail(component_id: int):
    """获取构件详情（含钢筋明细）"""
    comp = Component.query.get_or_404(component_id)
    details = RebarDetail.query.filter_by(component_id=component_id).order_by(RebarDetail.diameter).all()
    return comp, details


def update_component_status(component_id: int, new_status: str):
    """更新施工状态"""
    comp = Component.query.get_or_404(component_id)
    comp.status = new_status
    db.session.commit()
    return comp


def batch_update_status(component_ids: list, new_status: str):
    """批量更新施工状态"""
    count = Component.query.filter(Component.id.in_(component_ids)).update(
        {"status": new_status}, synchronize_session=False
    )
    db.session.commit()
    return count


def get_status_summary(project_id: int = None, building_id: str = None,
                       floor_id: str = None, area_id: str = None):
    """施工状态统计（吨数）"""
    query = db.session.query(
        Component.status,
        func.sum(RebarDetail.weight)
    ).join(RebarDetail).join(Area).join(Floor).join(Building)

    if building_id and building_id != "all":
        query = query.filter(Building.id == int(building_id))
    if floor_id and floor_id != "all":
        query = query.filter(Floor.id == int(floor_id))
    if area_id and area_id != "all":
        query = query.filter(Area.id == int(area_id))
    if project_id:
        query = query.filter(Building.project_id == project_id)

    results = query.group_by(Component.status).all()

    summary = {"poured": 0.0, "in_progress": 0.0, "not_started": 0.0, "total": 0.0}
    for status, weight in results:
        w = round(float(weight or 0), 3)
        summary[status] = w
        summary["total"] += w
    summary["total"] = round(summary["total"], 3)
    return summary


def get_diameter_summary(project_id: int = None, building_id: str = None):
    """按钢筋直径汇总"""
    query = db.session.query(
        RebarDetail.diameter,
        func.sum(RebarDetail.weight)
    ).join(Component).join(Area).join(Floor).join(Building)

    if building_id and building_id != "all":
        query = query.filter(Building.id == int(building_id))
    if project_id:
        query = query.filter(Building.project_id == project_id)

    results = query.group_by(RebarDetail.diameter).order_by(RebarDetail.diameter).all()
    return {int(d): round(float(w or 0), 3) for d, w in results}


def get_import_batches(project_id: int):
    """获取导入批次列表"""
    return ImportBatch.query.filter_by(project_id=project_id).order_by(ImportBatch.created_at.desc()).all()


def delete_batch(batch_id: int):
    """删除导入批次及其数据"""
    batch = ImportBatch.query.get_or_404(batch_id)
    # 删除该批次的所有钢筋明细和构件
    details = RebarDetail.query.filter_by(batch_id=batch_id).all()
    for d in details:
        db.session.delete(d)
    db.session.delete(batch)
    db.session.commit()
