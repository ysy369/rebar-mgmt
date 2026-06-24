"""结余率分析计算服务——从台账数据聚合到 project_analysis"""
from app import db
from app.models import ProjectAnalysis
from app.models.rebar import Incoming, Transfer, MeasureRebar, Inventory, Waste, ModelQuantity
from sqlalchemy import func


def recalc_project_analysis(project_id):
    """从原始台账数据重新计算项目分析指标"""
    pa = ProjectAnalysis.query.filter_by(project_id=project_id).first()
    if not pa:
        pa = ProjectAnalysis(project_id=project_id)
        db.session.add(pa)

    # 进场量(T)
    incoming = db.session.query(func.coalesce(func.sum(Incoming.weigh_weight), 0)).filter_by(project_id=project_id).scalar()
    pa.incoming_qty = round(float(incoming), 3)

    # 调拨量(T)
    transfer = db.session.query(func.coalesce(func.sum(Transfer.weight), 0)).filter_by(project_id=project_id, direction='out').scalar()
    pa.transfer_qty = round(float(transfer), 3)

    # 剩余量(盘点)
    remaining = db.session.query(func.coalesce(func.sum(Inventory.total_weight), 0)).filter_by(project_id=project_id).scalar()
    pa.remaining_qty = round(float(remaining), 3)

    # 废料量
    waste = db.session.query(func.coalesce(func.sum(Waste.waste_weight), 0)).filter_by(project_id=project_id).scalar()
    pa.waste_qty = round(float(waste), 3)

    # 措施筋量(T) - weight_kg 转 T
    measure = db.session.query(func.coalesce(func.sum(MeasureRebar.weight_kg), 0)).filter_by(project_id=project_id).scalar()
    pa.measure_qty = round(float(measure) / 1000, 3)

    # 模型量（主体结构量）
    model = db.session.query(func.coalesce(func.sum(ModelQuantity.structural_weight), 0)).filter_by(project_id=project_id).scalar()
    pa.struct_qty = round(float(model), 3)

    # 使用量 = 进场 - 剩余 - 废料 - 调拨 - 非预算 - 临建
    pa.usage_qty = round(pa.incoming_qty - pa.remaining_qty - pa.waste_qty - pa.transfer_qty - (pa.non_budget_use_qty or 0) - (pa.temp_facility_qty or 0), 3)

    # 对甲结算量：如果未设置，默认 = 施工图预算量（模型+措施筋+非实体-二构）
    if not pa.contract_qty or float(pa.contract_qty) == 0:
        pa.contract_qty = round(pa.struct_qty + pa.measure_qty + (pa.non_entity_qty or 0) - (pa.sec_struct_qty or 0), 3)
    if float(pa.contract_qty) == 0:
        pa.contract_qty = pa.incoming_qty  # fallback

    # 节约量 = 对甲结算 - 使用量
    pa.saved_qty = round(float(pa.contract_qty) - pa.usage_qty, 3)

    # 结余率
    if float(pa.contract_qty) > 0:
        pa.balance_rate = round(float(pa.saved_qty) / float(pa.contract_qty) * 100, 2)

    db.session.commit()
    return pa
