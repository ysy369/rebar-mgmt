# ============================================
# 钢筋精细化管理平台 — 首页深色科技数据看板
# ============================================
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_, extract, func as sql_func

from app import db
from app.models import Project, ProjectAnalysis, UserProject
from app.models.bom import ImportBatch, RebarDetail
from app.models.rebar import Incoming, Transfer, MeasureRebar, Inventory, Waste


dashboard_bp = Blueprint(
    "dashboard", __name__, template_folder="../templates/dashboard"
)


def _bc(*items):
    """构造统一面包屑：首页 + 各级节点"""
    base = [{"name": "钢筋管理平台", "url": url_for("dashboard.index")}]
    base.extend(items)
    return base


def _get_accessible_projects():
    """获取当前用户可访问的项目（管理员全部，普通用户授权）"""
    query = Project.query.filter_by(status="in_progress")
    if not current_user.is_admin:
        query = query.join(UserProject).filter(
            UserProject.user_id == current_user.id
        )
    return query.order_by(Project.updated_at.desc()).all()


def _parse_date_range(period, start_str, end_str):
    """根据筛选参数解析日期范围，返回 (date_from, date_to, period_label)"""
    now = datetime.utcnow()
    today = now.date()

    if period == "month":
        date_from = today.replace(day=1)
        # 月末
        if today.month == 12:
            date_to = today.replace(month=12, day=31)
        else:
            nxt = today.replace(month=today.month + 1, day=1)
            date_to = nxt - timedelta(days=1)
        return date_from, date_to, f"{today.year}年{today.month:02d}月"

    if period == "quarter":
        quarter = (today.month - 1) // 3 + 1
        month_from = (quarter - 1) * 3 + 1
        date_from = today.replace(month=month_from, day=1)
        if quarter == 4:
            date_to = today.replace(month=12, day=31)
        else:
            nxt = today.replace(month=quarter * 3 + 1, day=1)
            date_to = nxt - timedelta(days=1)
        return date_from, date_to, f"{today.year}年第{quarter}季度"

    if period == "year":
        date_from = today.replace(month=1, day=1)
        date_to = today.replace(month=12, day=31)
        return date_from, date_to, f"{today.year}年"

    if period == "custom":
        try:
            date_from = datetime.strptime(start_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            date_from = today.replace(day=1)
        try:
            date_to = datetime.strptime(end_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            date_to = today
        if date_from > date_to:
            date_from, date_to = date_to, date_from
        return date_from, date_to, f"{date_from} 至 {date_to}"

    # 默认 all
    return None, None, "全期累计"


def _date_filter(model, date_col, date_from, date_to):
    """构造日期范围过滤条件，返回 and_ 逻辑条件或 True"""
    col = getattr(model, date_col)
    conditions = []
    if date_from:
        conditions.append(col >= date_from)
    if date_to:
        conditions.append(col <= date_to)
    return and_(*conditions) if conditions else True


def _calc_all_period_stats(project_ids):
    """全期指标：从 project_analysis 汇总"""
    empty = {
        "contract_qty": 0.0,
        "usage_qty": 0.0,
        "saved_qty": 0.0,
        "incoming_qty": 0.0,
        "remaining_qty": 0.0,
        "waste_qty": 0.0,
        "transfer_qty": 0.0,
        "measure_qty": 0.0,
        "loss_rate": 0.0,
        "efficiency_rate": 0.0,
    }
    if not project_ids:
        return empty

    agg = (
        db.session.query(
            sql_func.sum(ProjectAnalysis.contract_qty),
            sql_func.sum(ProjectAnalysis.usage_qty),
            sql_func.sum(ProjectAnalysis.saved_qty),
            sql_func.sum(ProjectAnalysis.incoming_qty),
            sql_func.sum(ProjectAnalysis.remaining_qty),
            sql_func.sum(ProjectAnalysis.waste_qty),
            sql_func.sum(ProjectAnalysis.transfer_qty),
            sql_func.sum(ProjectAnalysis.measure_qty),
        )
        .filter(ProjectAnalysis.project_id.in_(project_ids))
        .first()
    )

    contract = float(agg[0] or 0)
    usage = float(agg[1] or 0)
    saved = float(agg[2] or 0)
    incoming = float(agg[3] or 0)
    waste = float(agg[5] or 0)

    loss_rate = round((waste / incoming * 100) if incoming > 0 else 0, 2)
    efficiency_rate = round((saved / contract * 100) if contract > 0 else 0, 2)

    return {
        "contract_qty": round(float(agg[0] or 0), 3),
        "usage_qty": round(usage, 3),
        "saved_qty": round(saved, 3),
        "incoming_qty": round(incoming, 3),
        "remaining_qty": round(float(agg[4] or 0), 3),
        "waste_qty": round(waste, 3),
        "transfer_qty": round(float(agg[6] or 0), 3),
        "measure_qty": round(float(agg[7] or 0), 3),
        "loss_rate": loss_rate,
        "efficiency_rate": efficiency_rate,
    }


def _calc_period_stats(project_ids, date_from, date_to):
    """按日期范围汇总指标（用于左栏选中周期）"""
    empty = {
        "contract_qty": 0.0,
        "usage_qty": 0.0,
        "saved_qty": 0.0,
        "incoming_qty": 0.0,
        "remaining_qty": 0.0,
        "waste_qty": 0.0,
        "transfer_qty": 0.0,
        "measure_qty": 0.0,
        "loss_rate": 0.0,
        "efficiency_rate": 0.0,
    }
    if not project_ids:
        return empty

    incoming = round(
        float(
            db.session.query(
                sql_func.coalesce(sql_func.sum(Incoming.weigh_weight), 0)
            )
            .filter(
                Incoming.project_id.in_(project_ids),
                and_(Incoming.date >= date_from, Incoming.date <= date_to),
            )
            .scalar()
        ),
        3,
    )

    transfer_out = round(
        float(
            db.session.query(sql_func.coalesce(sql_func.sum(Transfer.weight), 0))
            .filter(
                Transfer.project_id.in_(project_ids),
                Transfer.direction == "out",
                and_(Transfer.date >= date_from, Transfer.date <= date_to),
            )
            .scalar()
        ),
        3,
    )

    waste = round(
        float(
            db.session.query(sql_func.coalesce(sql_func.sum(Waste.waste_weight), 0))
            .filter(
                Waste.project_id.in_(project_ids),
                and_(Waste.process_date >= date_from, Waste.process_date <= date_to),
            )
            .scalar()
        ),
        3,
    )

    remaining = round(
        float(
            db.session.query(sql_func.coalesce(sql_func.sum(Inventory.total_weight), 0))
            .filter(
                Inventory.project_id.in_(project_ids),
                and_(Inventory.inventory_date >= date_from, Inventory.inventory_date <= date_to),
            )
            .scalar()
        ),
        3,
    )

    measure_kg = float(
        db.session.query(sql_func.coalesce(sql_func.sum(MeasureRebar.weight_kg), 0))
        .filter(
            MeasureRebar.project_id.in_(project_ids),
            and_(MeasureRebar.date >= date_from, MeasureRebar.date <= date_to),
        )
        .scalar()
    )
    measure = round(measure_kg / 1000, 3)

    # 使用量 = 进场 - 剩余 - 废料 - 调出 - 措施筋
    usage = round(incoming - remaining - waste - transfer_out - measure, 3)

    # 预算参考：以全期对甲结算量为基准
    contract = round(
        float(
            db.session.query(sql_func.coalesce(sql_func.sum(ProjectAnalysis.contract_qty), 0))
            .filter(ProjectAnalysis.project_id.in_(project_ids))
            .scalar()
        ),
        3,
    )
    saved = round(contract - usage, 3)
    loss_rate = round((waste / incoming * 100) if incoming > 0 else 0, 2)
    efficiency_rate = round((saved / contract * 100) if contract > 0 else 0, 2)

    return {
        "contract_qty": contract,
        "usage_qty": usage,
        "saved_qty": saved,
        "incoming_qty": incoming,
        "remaining_qty": remaining,
        "waste_qty": waste,
        "transfer_qty": transfer_out,
        "measure_qty": measure,
        "loss_rate": loss_rate,
        "efficiency_rate": efficiency_rate,
    }


def _calc_material_indices(project_ids, date_from=None, date_to=None):
    """物资指数：半原库存 / 调入 / 调出 / 进场 / 废旧 / 措施"""
    empty = {
        "semi_inventory": 0.0,
        "transfer_in": 0.0,
        "transfer_out": 0.0,
        "incoming": 0.0,
        "waste": 0.0,
        "measure": 0.0,
    }
    if not project_ids:
        return empty

    semi_inventory = round(
        float(
            db.session.query(sql_func.coalesce(sql_func.sum(Inventory.total_weight), 0))
            .filter(
                Inventory.project_id.in_(project_ids),
                Inventory.category == "semi",
                _date_filter(Inventory, "inventory_date", date_from, date_to),
            )
            .scalar()
        ),
        3,
    )

    transfer_in = round(
        float(
            db.session.query(sql_func.coalesce(sql_func.sum(Transfer.weight), 0))
            .filter(
                Transfer.project_id.in_(project_ids),
                Transfer.direction == "in",
                _date_filter(Transfer, "date", date_from, date_to),
            )
            .scalar()
        ),
        3,
    )

    transfer_out = round(
        float(
            db.session.query(sql_func.coalesce(sql_func.sum(Transfer.weight), 0))
            .filter(
                Transfer.project_id.in_(project_ids),
                Transfer.direction == "out",
                _date_filter(Transfer, "date", date_from, date_to),
            )
            .scalar()
        ),
        3,
    )

    incoming = round(
        float(
            db.session.query(sql_func.coalesce(sql_func.sum(Incoming.weigh_weight), 0))
            .filter(
                Incoming.project_id.in_(project_ids),
                _date_filter(Incoming, "date", date_from, date_to),
            )
            .scalar()
        ),
        3,
    )

    waste = round(
        float(
            db.session.query(sql_func.coalesce(sql_func.sum(Waste.waste_weight), 0))
            .filter(
                Waste.project_id.in_(project_ids),
                _date_filter(Waste, "process_date", date_from, date_to),
            )
            .scalar()
        ),
        3,
    )

    measure_kg = float(
        db.session.query(sql_func.coalesce(sql_func.sum(MeasureRebar.weight_kg), 0))
        .filter(
            MeasureRebar.project_id.in_(project_ids),
            _date_filter(MeasureRebar, "date", date_from, date_to),
        )
        .scalar()
    )
    measure = round(measure_kg / 1000, 3)

    return {
        "semi_inventory": semi_inventory,
        "transfer_in": transfer_in,
        "transfer_out": transfer_out,
        "incoming": incoming,
        "waste": waste,
        "measure": measure,
    }


def _calc_monthly_trend(project_ids, months=12):
    """计算最近 N 个月的三类进度趋势"""
    labels = []
    usage_data = []
    bom_data = []
    incoming_data = []

    now = datetime.utcnow()
    for i in range(months - 1, -1, -1):
        d = now - timedelta(days=i * 30)
        year, month = d.year, d.month
        labels.append(f"{month}月")

        incoming = float(
            db.session.query(sql_func.coalesce(sql_func.sum(Incoming.weigh_weight), 0))
            .filter(
                Incoming.project_id.in_(project_ids) if project_ids else False,
                extract("year", Incoming.date) == year,
                extract("month", Incoming.date) == month,
            )
            .scalar()
            or 0
        )
        transfer_out = float(
            db.session.query(sql_func.coalesce(sql_func.sum(Transfer.weight), 0))
            .filter(
                Transfer.project_id.in_(project_ids) if project_ids else False,
                Transfer.direction == "out",
                extract("year", Transfer.date) == year,
                extract("month", Transfer.date) == month,
            )
            .scalar()
            or 0
        )
        waste = float(
            db.session.query(sql_func.coalesce(sql_func.sum(Waste.waste_weight), 0))
            .filter(
                Waste.project_id.in_(project_ids) if project_ids else False,
                extract("year", Waste.process_date) == year,
                extract("month", Waste.process_date) == month,
            )
            .scalar()
            or 0
        )
        measure_kg = float(
            db.session.query(sql_func.coalesce(sql_func.sum(MeasureRebar.weight_kg), 0))
            .filter(
                MeasureRebar.project_id.in_(project_ids) if project_ids else False,
                extract("year", MeasureRebar.date) == year,
                extract("month", MeasureRebar.date) == month,
            )
            .scalar()
            or 0
        )
        usage = round(incoming - waste - transfer_out - measure_kg / 1000, 3)
        usage_data.append(max(usage, 0))
        incoming_data.append(round(incoming, 3))

        bom = round(
            float(
                db.session.query(sql_func.coalesce(sql_func.sum(RebarDetail.weight), 0))
                .join(ImportBatch)
                .filter(
                    ImportBatch.project_id.in_(project_ids) if project_ids else False,
                    extract("year", ImportBatch.created_at) == year,
                    extract("month", ImportBatch.created_at) == month,
                )
                .scalar()
                or 0
            ),
            3,
        )
        bom_data.append(bom)

    return {
        "labels": labels,
        "usage": usage_data,
        "bom": bom_data,
        "incoming": incoming_data,
    }


def _build_alerts(project_ids):
    """构建指数预警列表"""
    alerts = []
    if not project_ids:
        return alerts

    analyses = ProjectAnalysis.query.filter(
        ProjectAnalysis.project_id.in_(project_ids)
    ).all()
    project_map = {p.id: p for p in Project.query.filter(Project.id.in_(project_ids)).all()}

    for pa in analyses:
        project = project_map.get(pa.project_id)
        p_name = project.name if project else f"项目#{pa.project_id}"
        contract = float(pa.contract_qty or 0)
        usage = float(pa.usage_qty or 0)
        saved = float(pa.saved_qty or 0)
        rate = float(pa.balance_rate or 0)
        incoming = float(pa.incoming_qty or 0)

        if rate < 0:
            alerts.append({
                "project": p_name,
                "metric": "结余率",
                "value": f"{rate:.2f}%",
                "tag": "亏损",
                "tag_class": "danger",
                "desc": f"节约量 {saved:.1f}T，已出现亏损",
            })

        if contract > 0 and usage > contract:
            alerts.append({
                "project": p_name,
                "metric": "消耗量",
                "value": f"{usage:.1f}T",
                "tag": "超耗",
                "tag_class": "warning",
                "desc": f"超预算 {usage - contract:.1f}T",
            })

        if incoming == 0:
            alerts.append({
                "project": p_name,
                "metric": "进场量",
                "value": "0T",
                "tag": "无记录",
                "tag_class": "info",
                "desc": "暂无进场记录",
            })

    return alerts


def _kpi_status(value, metric):
    """根据指标返回状态标签与样式"""
    if metric == "loss_rate":
        if value <= 2:
            return "正常", "success"
        if value <= 5:
            return "关注", "warning"
        return "预警", "danger"
    if metric == "efficiency_rate":
        if value >= 5:
            return "正常", "success"
        if value >= 0:
            return "关注", "warning"
        return "预警", "danger"
    if metric == "usage":
        if value <= 0.9:
            return "正常", "success"
        if value <= 1.0:
            return "关注", "warning"
        return "预警", "danger"
    return "正常", "success"


@dashboard_bp.route("/dashboard")
@login_required
def index():
    """首页深色科技数据看板"""
    # ================= 改动2：日期筛选参数处理 =================
    period = request.args.get("period", "month").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    # 校验 period 取值
    if period not in ("all", "month", "quarter", "year", "custom"):
        period = "month"

    date_from, date_to, period_label = _parse_date_range(period, start_date, end_date)

    projects = _get_accessible_projects()
    project_ids = [p.id for p in projects]

    # 全期指标（右栏）
    all_stats = _calc_all_period_stats(project_ids)

    # 选中周期指标（左栏）
    if period == "all":
        selected_stats = all_stats
        material_selected = _calc_material_indices(project_ids)
    else:
        selected_stats = _calc_period_stats(project_ids, date_from, date_to)
        material_selected = _calc_material_indices(project_ids, date_from, date_to)

    # 进度趋势（保持 12 个月不变）
    trend = _calc_monthly_trend(project_ids)

    # 预警
    alerts = _build_alerts(project_ids)

    # KPI 状态
    selected_usage_ratio = (
        selected_stats["usage_qty"] / selected_stats["contract_qty"]
        if selected_stats["contract_qty"] > 0 else 0
    )
    all_usage_ratio = (
        all_stats["usage_qty"] / all_stats["contract_qty"]
        if all_stats["contract_qty"] > 0 else 0
    )

    selected_status = {
        "usage_label": _kpi_status(selected_usage_ratio, "usage")[0],
        "usage_class": _kpi_status(selected_usage_ratio, "usage")[1],
        "loss_label": _kpi_status(selected_stats["loss_rate"], "loss_rate")[0],
        "loss_class": _kpi_status(selected_stats["loss_rate"], "loss_rate")[1],
        "efficiency_label": _kpi_status(selected_stats["efficiency_rate"], "efficiency_rate")[0],
        "efficiency_class": _kpi_status(selected_stats["efficiency_rate"], "efficiency_rate")[1],
    }
    all_status = {
        "usage_label": _kpi_status(all_usage_ratio, "usage")[0],
        "usage_class": _kpi_status(all_usage_ratio, "usage")[1],
        "loss_label": _kpi_status(all_stats["loss_rate"], "loss_rate")[0],
        "loss_class": _kpi_status(all_stats["loss_rate"], "loss_rate")[1],
        "efficiency_label": _kpi_status(all_stats["efficiency_rate"], "efficiency_rate")[0],
        "efficiency_class": _kpi_status(all_stats["efficiency_rate"], "efficiency_rate")[1],
    }

    # ===== 前期（上月）对比数据 =====
    now = datetime.utcnow()
    prev_month = now.month - 1 if now.month > 1 else 12
    prev_year = now.year if now.month > 1 else now.year - 1
    prev_from = datetime(prev_year, prev_month, 1)
    if prev_month == 12:
        prev_to = datetime(prev_year + 1, 1, 1) - timedelta(seconds=1)
    else:
        prev_to = datetime(prev_year, prev_month + 1, 1) - timedelta(seconds=1)

    prev_stats = _calc_period_stats(project_ids, prev_from, prev_to)
    material_prev = _calc_material_indices(project_ids, prev_from, prev_to)
    prev_usage_ratio = (
        prev_stats["usage_qty"] / prev_stats["contract_qty"]
        if prev_stats["contract_qty"] > 0 else 0
    )
    prev_status = {
        "usage_label": _kpi_status(prev_usage_ratio, "usage")[0],
        "usage_class": _kpi_status(prev_usage_ratio, "usage")[1],
        "loss_label": _kpi_status(prev_stats["loss_rate"], "loss_rate")[0],
        "loss_class": _kpi_status(prev_stats["loss_rate"], "loss_rate")[1],
        "efficiency_label": _kpi_status(prev_stats["efficiency_rate"], "efficiency_rate")[0],
        "efficiency_class": _kpi_status(prev_stats["efficiency_rate"], "efficiency_rate")[1],
    }
    prev_label = f"{prev_year}年{prev_month}月"

    # ================= 改动3：顶部导航菜单路由 =================
    nav_menu = [
        {"name": "数据看板", "url": url_for("dashboard.index"), "active": True, "visible": True},
        {"name": "钢筋台账", "url": url_for("project.project_list"), "active": False, "visible": True},
        {"name": "方样料单", "url": url_for("bom.dashboard"), "active": False, "visible": True},
        {"name": "项目管理", "url": url_for("admin.project_list"), "active": False, "visible": current_user.is_admin},
        {"name": "料单审核", "url": url_for("admin.cutting_order_list"), "active": False, "visible": current_user.is_admin},
        {"name": "盈亏分析", "url": url_for("admin.pl_dashboard"), "active": False, "visible": current_user.is_admin},
        {"name": "用户管理", "url": url_for("admin.user_list"), "active": False, "visible": current_user.is_admin},
    ]

    return render_template(
        "dashboard/index.html",
        projects=projects,
        project_ids=project_ids,
        current_period=period,
        period_label=period_label,
        start_date=start_date,
        end_date=end_date,
        date_from=date_from,
        date_to=date_to,
        current_date=datetime.utcnow().date(),
        current_year=datetime.utcnow().year,
        current_month=datetime.utcnow().month,
        selected_stats=selected_stats,
        all_stats=all_stats,
        selected_status=selected_status,
        all_status=all_status,
        material_selected=material_selected,
        material_all=_calc_material_indices(project_ids),
        material_prev=material_prev,
        trend=trend,
        alerts=alerts,
        all_dashboard_projects=Project.query.order_by(Project.name).all(),
        selected_project_ids=request.args.getlist("project_ids", type=int),
        prev_stats=prev_stats,
        prev_status=prev_status,
        prev_label=prev_label,
        period_label_all=period_label,
        nav_menu=nav_menu,
        breadcrumbs=_bc(),
        page_title="数据看板",
    )
