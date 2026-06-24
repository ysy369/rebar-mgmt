# ============================================
# 钢筋精细化管理平台 — 项目成本服务
# ============================================
from datetime import datetime

from app import db
from app.models.business import ProjectCost

CATEGORY_LABELS = {
    "labor": "人工费",
    "material": "材料费",
    "equipment": "机械费",
    "transport": "运输费",
    "management": "管理费",
    "other": "其他",
}


def get_category_label(cat: str) -> str:
    return CATEGORY_LABELS.get(cat, cat)


def get_project_costs(project_id: int):
    return (
        ProjectCost.query.filter_by(project_id=project_id)
        .order_by(ProjectCost.cost_date.desc())
        .all()
    )


def get_cost_summary(project_id: int):
    """按类别汇总成本"""
    costs = get_project_costs(project_id)
    summary = {}
    total = 0
    for c in costs:
        cat = c.cost_category
        if cat not in summary:
            summary[cat] = {"label": get_category_label(cat), "amount": 0, "count": 0}
        summary[cat]["amount"] += float(c.amount or 0)
        summary[cat]["count"] += 1
        total += float(c.amount or 0)
    return {"categories": summary, "total": round(total, 2)}


def get_cost_by_id(cost_id: int) -> ProjectCost:
    return ProjectCost.query.get_or_404(cost_id)


def create_cost(project_id: int, cost_date: str, cost_category: str,
                cost_item: str, amount: float, description: str = None,
                receipt_no: str = None, created_by: int = None) -> ProjectCost:
    c = ProjectCost(
        project_id=project_id,
        cost_date=datetime.strptime(cost_date, "%Y-%m-%d").date(),
        cost_category=cost_category,
        cost_item=cost_item,
        amount=amount,
        description=description,
        receipt_no=receipt_no,
        created_by=created_by,
    )
    db.session.add(c)
    db.session.commit()
    return c


def update_cost(cost_id: int, **kwargs) -> ProjectCost:
    c = get_cost_by_id(cost_id)
    for key in ["cost_date", "cost_category", "cost_item", "amount", "description", "receipt_no"]:
        if key in kwargs and kwargs[key] is not None:
            if key == "cost_date":
                kwargs[key] = datetime.strptime(kwargs[key], "%Y-%m-%d").date()
            elif key == "amount":
                kwargs[key] = float(kwargs[key])
            setattr(c, key, kwargs[key])
    db.session.commit()
    return c


def delete_cost(cost_id: int):
    c = get_cost_by_id(cost_id)
    db.session.delete(c)
    db.session.commit()
