# ============================================
# 钢筋精细化管理平台 — 项目盈亏分析服务
# ============================================
from app import db
from app.models import Project, ProjectAnalysis
from app.models.business import ProjectCost, ProjectProfitLoss


def recompute_project_pl(project_id: int) -> ProjectProfitLoss:
    """重新计算项目盈亏（从源数据拉取）"""
    # 获取节约量
    saved_qty = 0.0
    analysis = ProjectAnalysis.query.filter_by(project_id=project_id).first()
    if analysis and analysis.saved_qty:
        saved_qty = float(analysis.saved_qty)

    # 获取总成本
    costs = ProjectCost.query.filter_by(project_id=project_id).all()
    total_cost = sum(float(c.amount or 0) for c in costs)

    # 获取或创建 P&L 记录
    pl = ProjectProfitLoss.query.filter_by(project_id=project_id).first()
    if not pl:
        pl = ProjectProfitLoss(project_id=project_id)
        db.session.add(pl)

    # 计算
    rebar_unit_price = float(pl.rebar_unit_price or 5000)
    pl.rebar_saved_qty = saved_qty
    pl.rebar_income = round(saved_qty * rebar_unit_price, 2)
    pl.total_cost = round(total_cost, 2)
    pl.total_income = round(pl.rebar_income + float(pl.other_income or 0), 2)
    pl.net_profit = round(pl.total_income - pl.total_cost, 2)
    if pl.total_income > 0:
        pl.profit_rate = round(pl.net_profit / pl.total_income * 100, 2)
    else:
        pl.profit_rate = 0

    db.session.commit()
    return pl


def get_project_pl(project_id: int) -> ProjectProfitLoss:
    """获取盈亏记录（自动计算）"""
    return recompute_project_pl(project_id)


def update_unit_price(project_id: int, unit_price: float):
    """更新钢筋节约定价"""
    pl = ProjectProfitLoss.query.filter_by(project_id=project_id).first()
    if not pl:
        pl = ProjectProfitLoss(project_id=project_id)
        db.session.add(pl)
    pl.rebar_unit_price = unit_price
    db.session.commit()
    recompute_project_pl(project_id)


def update_other_income(project_id: int, amount: float):
    """更新其他收入"""
    pl = ProjectProfitLoss.query.filter_by(project_id=project_id).first()
    if not pl:
        pl = ProjectProfitLoss(project_id=project_id)
        db.session.add(pl)
    pl.other_income = amount
    db.session.commit()
    recompute_project_pl(project_id)


def get_all_projects_pl():
    """获取所有项目的盈亏数据（管理员跨项目视图）"""
    projects = Project.query.filter_by(status="in_progress").all()
    result = []
    for p in projects:
        pl = recompute_project_pl(p.id)
        result.append({
            "project": p,
            "pl": pl,
        })
    return result
