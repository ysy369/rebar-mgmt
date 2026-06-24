"""全量数据导入脚本"""
import pandas as pd, os, sys
sys.path.insert(0, '/app')
from app import create_app, db
from app.models import Incoming, Transfer, MeasureRebar, Inventory, Waste, ModelQuantity, ProjectAnalysis
from app.models.building_progress import BuildingProgress
from datetime import datetime

app = create_app()
PID = 1

def pdate(v):
    if pd.isna(v) or v in ('', None): return datetime.utcnow().date()
    if isinstance(v, datetime): return v.date()
    try: return pd.to_datetime(v).date()
    except: return datetime.utcnow().date()

def pfloat(v, d=0):
    try:
        if pd.isna(v) or v in ('', None): return d
        return float(v)
    except: return d

def pint(v, d=0):
    try:
        if pd.isna(v) or v in ('', None): return d
        return int(float(v))
    except: return d

with app.app_context():
    # 清空旧数据
    Waste.query.filter_by(project_id=PID).delete()
    Inventory.query.filter_by(project_id=PID).delete()
    MeasureRebar.query.filter_by(project_id=PID).delete()
    Transfer.query.filter_by(project_id=PID).delete()
    Incoming.query.filter_by(project_id=PID).delete()
    BuildingProgress.query.filter_by(project_id=PID).delete()
    db.session.commit()
    print("旧数据已清除")

    # ===== 1. 进场台账 =====
    print("--- 进场台账 ---")
    f3 = "/app/tests/3、钢筋进场验收、钢筋进场确认单、调拨确认单、废料处理台账.xlsx"
    xl3 = pd.ExcelFile(f3)
    for sn in xl3.sheet_names:
        df = pd.read_excel(f3, sheet_name=sn, header=None)
        for i in range(3, len(df)):
            row = df.iloc[i]
            try:
                wt = pfloat(row.iloc[12] if len(df.columns) > 12 else row.iloc[9])
                if wt <= 0: continue
                db.session.add(Incoming(
                    project_id=PID, date=pdate(row.iloc[1]),
                    receipt_no=str(row.iloc[2]) if pd.notna(row.iloc[2]) else None,
                    brand=str(row.iloc[3]) if pd.notna(row.iloc[3]) else None,
                    product_name=str(row.iloc[4]) if pd.notna(row.iloc[4]) else None,
                    spec=str(row.iloc[5]) if pd.notna(row.iloc[5]) else '',
                    material=str(row.iloc[6]) if pd.notna(row.iloc[6]) else None,
                    rebar_length=pfloat(row.iloc[7]) if pd.notna(row.iloc[7]) else None,
                    piece_count=pint(row.iloc[8]),
                    theory_weight=pfloat(row.iloc[9]),
                    weigh_weight=wt, created_by=1,
                ))
            except: pass
    db.session.commit()
    print(f"进场: {Incoming.query.filter_by(project_id=PID).count()} 条")

    # ===== 2. 调拨 =====
    print("--- 调拨台账 ---")
    for sn in xl3.sheet_names:
        df = pd.read_excel(f3, sheet_name=sn, header=None)
        for i in range(2, len(df)):
            row = df.iloc[i]
            try:
                wt = pfloat(row.iloc[3] if len(df.columns) > 3 else 0)
                if wt <= 0: continue
                db.session.add(Transfer(
                    project_id=PID, date=pdate(row.iloc[0]),
                    spec=str(row.iloc[1]) if pd.notna(row.iloc[1]) else '',
                    piece_count=pint(row.iloc[2]), weight=wt,
                    direction='out', transfer_type='raw',
                    remark=str(row.iloc[4]) if len(df.columns) > 4 and pd.notna(row.iloc[4]) else '',
                    created_by=1,
                ))
            except: pass
    db.session.commit()
    print(f"调拨: {Transfer.query.filter_by(project_id=PID).count()} 条")

    # ===== 3. 措施筋 =====
    print("--- 措施筋台账 ---")
    f4 = "/app/tests/4、措施筋台账及申请表.xlsx"
    df4 = pd.read_excel(f4, header=None)
    for i in range(2, len(df4)):
        row = df4.iloc[i]
        try:
            wt = pfloat(row.iloc[8] if len(df4.columns) > 8 else 0)
            if wt <= 0: continue
            db.session.add(MeasureRebar(
                project_id=PID, date=pdate(row.iloc[1]),
                seq_no=str(row.iloc[0]) if pd.notna(row.iloc[0]) else None,
                unit_name=str(row.iloc[2]) if pd.notna(row.iloc[2]) else '',
                work_type=str(row.iloc[3]) if pd.notna(row.iloc[3]) else '',
                use_location=str(row.iloc[4]) if pd.notna(row.iloc[4]) else '',
                usage_purpose=str(row.iloc[5]) if pd.notna(row.iloc[5]) else '',
                spec_hrb400=str(row.iloc[6]) if pd.notna(row.iloc[6]) else '',
                spec_hpb300=str(row.iloc[7]) if pd.notna(row.iloc[7]) else '',
                weight_kg=wt, category='non_budget', created_by=1,
            ))
        except: pass
    db.session.commit()
    print(f"措施筋: {MeasureRebar.query.filter_by(project_id=PID).count()} 条")

    # ===== 4. 盘点表 =====
    print("--- 盘点表 ---")
    f7 = "/app/tests/7、钢筋盘点表.xlsx"
    xl7 = pd.ExcelFile(f7)
    for sn in xl7.sheet_names:
        df7 = pd.read_excel(f7, sheet_name=sn, header=None)
        for i in range(3, len(df7)):
            row = df7.iloc[i]
            try:
                tw = pfloat(row.iloc[5] if len(df7.columns) > 5 else 0)
                if tw <= 0: continue
                cat = str(row.iloc[1]) if pd.notna(row.iloc[1]) else 'raw'
                cmap = {'钢筋原材': 'raw', '短料余头': 'short', '半成品': 'semi'}
                db.session.add(Inventory(
                    project_id=PID, inventory_date=datetime.utcnow().date(),
                    category=cmap.get(cat.split('H')[0].strip(), 'raw'),
                    spec=str(row.iloc[2]) if pd.notna(row.iloc[2]) else '',
                    piece_count=pint(row.iloc[3]),
                    unit_weight=pfloat(row.iloc[4]),
                    total_weight=tw, created_by=1,
                ))
            except: pass
    db.session.commit()
    print(f"盘点: {Inventory.query.filter_by(project_id=PID).count()} 条")

    # ===== 5. 废料 =====
    print("--- 废料台账 ---")
    for sn in xl3.sheet_names:
        dfw = pd.read_excel(f3, sheet_name=sn, header=None)
        for i in range(2, len(dfw)):
            row = dfw.iloc[i]
            try:
                wt = pfloat(row.iloc[6] if len(dfw.columns) > 6 else 0)
                if wt <= 0: continue
                db.session.add(Waste(
                    project_id=PID, process_date=pdate(row.iloc[1]),
                    vehicle_before=pfloat(row.iloc[4]) if len(dfw.columns) > 4 else 0,
                    vehicle_after=pfloat(row.iloc[5]) if len(dfw.columns) > 5 else 0,
                    waste_weight=wt,
                    labor_team=str(row.iloc[11]) if len(dfw.columns) > 11 and pd.notna(row.iloc[11]) else '',
                    created_by=1,
                ))
            except: pass
    db.session.commit()
    print(f"废料: {Waste.query.filter_by(project_id=PID).count()} 条")

    # ===== 6. 大美项目形象进度 =====
    print("--- 形象进度 ---")
    fd = "/app/tests/大美项目结算上报资料.xlsx"
    if os.path.exists(fd):
        xld = pd.ExcelFile(fd)
        for sn in xld.sheet_names:
            if sn in ('结算申请表', '钢筋利润率明细', '（全部）结余率'): continue
            dfd = pd.read_excel(fd, sheet_name=sn, header=None)
            for i in range(2, len(dfd)):
                row = dfd.iloc[i]
                try:
                    tw = pfloat(row.iloc[2] if len(dfd.columns) > 2 else 0)
                    if tw <= 0: continue
                    db.session.add(BuildingProgress(
                        project_id=PID, building_name=str(row.iloc[0]) if pd.notna(row.iloc[0]) else sn,
                        floor_name=str(row.iloc[1]) if pd.notna(row.iloc[1]) else '',
                        component_type=sn, progress_status='done' if '已完工' in sn else '施工中',
                        total_weight=tw, record_date=datetime.utcnow().date(),
                    ))
                except: pass
        db.session.commit()

    # 形象进度Excel
    fimg = "/app/tests/形象进度.xlsx"
    if os.path.exists(fimg):
        xli = pd.ExcelFile(fimg)
        df_stat = pd.read_excel(fimg, sheet_name='统计表', header=None)
        for i in range(3, len(df_stat)):
            row = df_stat.iloc[i]
            try:
                bldg = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
                if not bldg or bldg == 'nan': continue
                db.session.add(BuildingProgress(
                    project_id=PID, building_name=bldg,
                    progress_status='done' if str(row.iloc[2]) == '已完成' else '施工中',
                    model_total=pfloat(row.iloc[3]) if len(df_stat.columns) > 3 else 0,
                    progress_qty=pfloat(row.iloc[4]) if len(df_stat.columns) > 4 else 0,
                    record_date=datetime.utcnow().date(),
                ))
            except: pass
        for sn in xli.sheet_names:
            if sn == '统计表': continue
            dfb = pd.read_excel(fimg, sheet_name=sn, header=None)
            for i in range(2, len(dfb)):
                row = dfb.iloc[i]
                try:
                    tw = pfloat(row.iloc[2] if len(dfb.columns) > 2 else 0)
                    if tw <= 0: continue
                    db.session.add(BuildingProgress(
                        project_id=PID, building_name=sn,
                        floor_name=str(row.iloc[0]) if pd.notna(row.iloc[0]) else '',
                        component_type=str(row.iloc[1]) if pd.notna(row.iloc[1]) else '',
                        total_weight=tw, record_date=datetime.utcnow().date(),
                    ))
                except: pass
        db.session.commit()
    print(f"形象进度: {BuildingProgress.query.filter_by(project_id=PID).count()} 条")

    # ===== 7. 重新计算 =====
    from app.services.analysis_service import recalc_project_analysis
    pa = recalc_project_analysis(PID)

    print("")
    print("========== 汇总 ==========")
    print(f"进场: {Incoming.query.filter_by(project_id=PID).count()} 条, {pa.incoming_qty}T")
    print(f"调拨: {Transfer.query.filter_by(project_id=PID).count()} 条, {pa.transfer_qty}T")
    print(f"措施筋: {MeasureRebar.query.filter_by(project_id=PID).count()} 条, {pa.measure_qty}T")
    print(f"盘点: {Inventory.query.filter_by(project_id=PID).count()} 条, {pa.remaining_qty}T")
    print(f"废料: {Waste.query.filter_by(project_id=PID).count()} 条, {pa.waste_qty}T")
    print(f"形象进度: {BuildingProgress.query.filter_by(project_id=PID).count()} 条")
    print(f"对甲结算: {pa.contract_qty}T | 使用量: {pa.usage_qty}T | 节约: {pa.saved_qty}T | 结余率: {pa.balance_rate}%")
    print("==========================")
