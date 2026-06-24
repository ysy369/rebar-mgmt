# ============================================
# 钢筋精细化管理平台 — 料单审核台账服务
# ============================================
from datetime import datetime

from app import db
from app.models.business import CuttingOrder, CuttingOrderItem

# 状态转换规则
ALLOWED_TRANSITIONS = {
    "draft": ["submitted"],
    "submitted": ["reviewed"],
    "reviewed": ["approved", "rejected"],
    "rejected": ["draft"],  # 驳回后可修改重提
    "approved": [],  # 终态
}


def can_transition(current_status: str, new_status: str) -> bool:
    """检查状态转换是否合法"""
    return new_status in ALLOWED_TRANSITIONS.get(current_status, [])


def generate_order_no(project_id: int) -> str:
    """生成料单单号: LD-YYYYMMDD-XXX"""
    today = datetime.utcnow().strftime("%Y%m%d")
    count = (
        CuttingOrder.query.filter(
            CuttingOrder.project_id == project_id,
            CuttingOrder.order_no.like(f"LD-{today}-%"),
        ).count()
        + 1
    )
    return f"LD-{today}-{count:03d}"


# ===== 料单主表 CRUD =====

def get_project_orders(project_id: int):
    """获取项目的所有料单，返回查询对象"""
    return (
        CuttingOrder.query.filter_by(project_id=project_id)
        .order_by(CuttingOrder.updated_at.desc())
    )


def get_all_orders(filters=None):
    """获取所有料单（管理员视图），支持筛选，返回查询对象"""
    query = CuttingOrder.query
    if filters:
        if filters.get("project_id"):
            query = query.filter_by(project_id=filters["project_id"])
        if filters.get("status"):
            query = query.filter_by(status=filters["status"])
    return query.order_by(CuttingOrder.updated_at.desc())


def get_order_by_id(order_id: int) -> CuttingOrder:
    """获取单个料单"""
    return CuttingOrder.query.get_or_404(order_id)


def create_order(project_id: int, order_date: str, batch_no: str = None,
                 labor_team: str = None, use_location: str = None,
                 remark: str = None, created_by: int = None) -> CuttingOrder:
    """创建料单（草稿）"""
    order = CuttingOrder(
        project_id=project_id,
        order_no=generate_order_no(project_id),
        order_date=datetime.strptime(order_date, "%Y-%m-%d").date(),
        batch_no=batch_no,
        labor_team=labor_team,
        use_location=use_location,
        status="draft",
        created_by=created_by,
    )
    db.session.add(order)
    db.session.commit()
    return order


def update_order(order_id: int, **kwargs) -> CuttingOrder:
    """更新料单（仅草稿/驳回状态可编辑）"""
    order = get_order_by_id(order_id)
    if order.status not in ("draft", "rejected"):
        raise ValueError(f"料单状态为 {order.status}，不可编辑")
    for key in ["order_date", "batch_no", "labor_team", "use_location", "remark"]:
        if key in kwargs and kwargs[key] is not None:
            if key == "order_date":
                kwargs[key] = datetime.strptime(kwargs[key], "%Y-%m-%d").date()
            setattr(order, key, kwargs[key])
    recalc_order_totals(order_id)
    db.session.commit()
    return order


def delete_order(order_id: int):
    """删除料单（仅草稿可删除）"""
    order = get_order_by_id(order_id)
    if order.status not in ("draft",):
        raise ValueError(f"料单状态为 {order.status}，不可删除")
    db.session.delete(order)
    db.session.commit()


# ===== 料单明细 CRUD =====

def get_order_items(order_id: int):
    """获取料单的所有明细行"""
    return (
        CuttingOrderItem.query.filter_by(order_id=order_id)
        .order_by(CuttingOrderItem.line_no)
        .all()
    )


def add_order_item(order_id: int, line_no: int, spec: str,
                   rebar_diameter: str = None, cut_length: float = None,
                   piece_count: int = None, unit_weight: float = None,
                   rebar_shape: str = None, component_name: str = None,
                   remark: str = None) -> CuttingOrderItem:
    """添加料单明细行"""
    order = get_order_by_id(order_id)
    if order.status not in ("draft", "rejected"):
        raise ValueError("料单状态不可编辑")

    item = CuttingOrderItem(
        order_id=order_id,
        line_no=line_no,
        spec=spec,
        rebar_diameter=rebar_diameter,
        cut_length=cut_length,
        piece_count=piece_count,
        unit_weight=unit_weight,
        rebar_shape=rebar_shape,
        component_name=component_name,
        remark=remark,
    )
    # 自动计算单根重量: total_weight = cut_length/1000 * unit_weight * piece_count
    if cut_length and piece_count:
        # unit_weight 单位是 kg/m，cut_length 单位是 mm
        item.total_weight = round(cut_length / 1000 * (unit_weight or 0.888) * piece_count, 3)

    db.session.add(item)
    db.session.commit()
    recalc_order_totals(order_id)
    return item


def update_order_item(item_id: int, **kwargs) -> CuttingOrderItem:
    """更新明细行"""
    item = CuttingOrderItem.query.get_or_404(item_id)
    order = item.order
    if order.status not in ("draft", "rejected"):
        raise ValueError("料单状态不可编辑")

    for key in ["line_no", "spec", "rebar_diameter", "cut_length",
                "piece_count", "unit_weight", "rebar_shape", "component_name", "remark"]:
        if key in kwargs and kwargs[key] is not None:
            setattr(item, key, kwargs[key])

    # 重新计算
    cl = float(item.cut_length or 0)
    pc = int(item.piece_count or 0)
    uw = float(item.unit_weight or 0.888)
    if cl and pc:
        item.total_weight = round(cl / 1000 * uw * pc, 3)

    db.session.commit()
    recalc_order_totals(item.order_id)
    return item


def delete_order_item(item_id: int):
    """删除明细行"""
    item = CuttingOrderItem.query.get_or_404(item_id)
    order_id = item.order_id
    order = item.order
    if order.status not in ("draft", "rejected"):
        raise ValueError("料单状态不可编辑")
    db.session.delete(item)
    db.session.commit()
    recalc_order_totals(order_id)


def recalc_order_totals(order_id: int):
    """重新计算料单的总根数和总重量"""
    items = get_order_items(order_id)
    total_pieces = sum(i.piece_count or 0 for i in items)
    total_weight = sum(float(i.total_weight or 0) for i in items)
    order = get_order_by_id(order_id)
    order.total_pieces = total_pieces
    order.total_weight = round(total_weight, 3)
    db.session.commit()


# ===== 审核流程 =====

def submit_order(order_id: int, user_id: int):
    """提交审核"""
    order = get_order_by_id(order_id)
    if not can_transition(order.status, "submitted"):
        raise ValueError(f"当前状态 {order.status} 不可提交")
    order.status = "submitted"
    order.submitted_by = user_id
    order.submitted_at = datetime.utcnow()
    db.session.commit()


def review_order(order_id: int, action: str, user_id: int, comment: str = None):
    """审核：approved 或 rejected"""
    order = get_order_by_id(order_id)
    if action not in ("approved", "rejected"):
        raise ValueError("审核操作只能是 approved 或 rejected")
    if not can_transition(order.status, "reviewed"):
        raise ValueError(f"当前状态 {order.status} 不可审核，需先标记为已审核")
    order.status = action
    order.reviewed_by = user_id
    order.reviewed_at = datetime.utcnow()
    order.review_comment = comment
    db.session.commit()


def mark_reviewed(order_id: int, user_id: int):
    """标记为已审核（中间状态）"""
    order = get_order_by_id(order_id)
    if not can_transition(order.status, "reviewed"):
        raise ValueError(f"当前状态 {order.status} 不可标记")
    order.status = "reviewed"
    order.reviewed_by = user_id
    order.reviewed_at = datetime.utcnow()
    db.session.commit()
