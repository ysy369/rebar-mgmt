"""钢筋台账数据导入服务——解析真实Excel模板"""
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import pandas as pd
from app import db
from app.models import Incoming, Transfer, MeasureRebar, Inventory, Waste

ALLOWED_EXT = {'.xlsx', '.xls'}


def save_upload(file, upload_dir):
    """保存上传文件"""
    os.makedirs(upload_dir, exist_ok=True)
    safe = secure_filename(file.filename)
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    path = os.path.join(upload_dir, f"{ts}_{safe}")
    file.save(path)
    return path


def parse_date(val):
    """通用日期解析"""
    if pd.isna(val) or val == '' or val is None:
        return datetime.utcnow().date()
    if isinstance(val, datetime):
        return val.date()
    try:
        return pd.to_datetime(val).date()
    except:
        return datetime.utcnow().date()


def import_incoming(file_path, project_id, user_id):
    """导入进场台账——匹配真实模板列: 序号/日期/单号/品牌/品名/规格/材质/型号/件数/理论重/过磅重①/车重②/钢筋重③"""
    df = pd.read_excel(file_path, header=None)
    success, failed = 0, 0
    for idx in range(3, len(df)):
        try:
            row = df.iloc[idx]
            seq = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
            if not seq.isdigit():
                continue  # skip empty/merged rows
            date = parse_date(row.iloc[1])
            receipt = str(row.iloc[2]) if pd.notna(row.iloc[2]) else None
            brand = str(row.iloc[3]) if pd.notna(row.iloc[3]) else None
            product = str(row.iloc[4]) if pd.notna(row.iloc[4]) else None
            spec = str(row.iloc[5]) if pd.notna(row.iloc[5]) else ''
            # 跳过无规格的空行
            if not spec or spec.strip() == 'nan' or spec.strip() == '':
                continue
            material = str(row.iloc[6]) if pd.notna(row.iloc[6]) else None
            rebar_len = float(row.iloc[7]) if pd.notna(row.iloc[7]) and row.iloc[7] != '' else None
            pieces = int(row.iloc[8]) if pd.notna(row.iloc[8]) and row.iloc[8] != '' else None
            theory = float(row.iloc[9]) if pd.notna(row.iloc[9]) and row.iloc[9] != '' else 0
            vehicle_gross = float(row.iloc[10]) if pd.notna(row.iloc[10]) and row.iloc[10] != '' else None
            vehicle_tare = float(row.iloc[11]) if pd.notna(row.iloc[11]) and row.iloc[11] != '' else None
            weigh = float(row.iloc[12]) if len(row) > 12 and pd.notna(row.iloc[12]) and row.iloc[12] != '' else 0

            db.session.add(Incoming(
                project_id=project_id, date=date, receipt_no=receipt,
                brand=brand, product_name=product, spec=f"{material or ''} {spec}",
                material=material, rebar_length=rebar_len,
                piece_count=pieces, theory_weight=theory,
                weigh_weight=weigh if weigh > 0 else (vehicle_gross or 0) - (vehicle_tare or 0),
                vehicle_gross=vehicle_gross, vehicle_tare=vehicle_tare,
                created_by=user_id,
            ))
            success += 1
        except Exception as e:
            failed += 1
    db.session.commit()
    return success, failed


def import_transfer(file_path, project_id, user_id):
    """导入调拨台账"""
    df = pd.read_excel(file_path, header=None)
    success, failed = 0, 0
    for idx in range(2, len(df)):
        try:
            row = df.iloc[idx]
            date = parse_date(row.iloc[0])
            spec = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ''
            count = int(row.iloc[2]) if pd.notna(row.iloc[2]) else 0
            weight = float(row.iloc[3]) if pd.notna(row.iloc[3]) else 0
            if weight > 0:
                db.session.add(Transfer(
                    project_id=project_id, date=date,
                    transfer_type='raw', direction='out',
                    spec=spec, piece_count=count, weight=weight,
                    remark=str(row.iloc[4]) if pd.notna(row.iloc[4]) else '',
                    created_by=user_id,
                ))
                success += 1
        except:
            failed += 1
    db.session.commit()
    return success, failed


def import_measure(file_path, project_id, user_id):
    """导入措施筋台账"""
    df = pd.read_excel(file_path, header=None)
    success, failed = 0, 0
    for idx in range(2, len(df)):
        try:
            row = df.iloc[idx]
            date = parse_date(row.iloc[1]) if pd.notna(row.iloc[1]) else datetime.utcnow().date()
            unit = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ''
            work = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ''
            location = str(row.iloc[4]) if pd.notna(row.iloc[4]) else ''
            purpose = str(row.iloc[5]) if pd.notna(row.iloc[5]) else ''
            spec400 = str(row.iloc[6]) if pd.notna(row.iloc[6]) else ''
            spec300 = str(row.iloc[7]) if pd.notna(row.iloc[7]) else ''
            weight = float(row.iloc[8]) if pd.notna(row.iloc[8]) else 0
            if weight > 0:
                db.session.add(MeasureRebar(
                    project_id=project_id, date=date,
                    unit_name=unit, work_type=work,
                    use_location=location, usage_purpose=purpose,
                    spec_hrb400=spec400, spec_hpb300=spec300,
                    weight_kg=weight, category='non_budget',
                    created_by=user_id,
                ))
                success += 1
        except:
            failed += 1
    db.session.commit()
    return success, failed


def import_inventory(file_path, project_id, user_id):
    """导入盘点表"""
    df = pd.read_excel(file_path, header=None)
    success, failed = 0, 0
    for idx in range(3, len(df)):
        try:
            row = df.iloc[idx]
            cat = str(row.iloc[1]) if pd.notna(row.iloc[1]) else 'raw'
            spec = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ''
            count = int(row.iloc[3]) if pd.notna(row.iloc[3]) else 0
            uw = float(row.iloc[4]) if pd.notna(row.iloc[4]) else 0
            tw = float(row.iloc[5]) if pd.notna(row.iloc[5]) else 0
            if tw > 0:
                cat_map = {'钢筋原材': 'raw', '短料余头': 'short', '半成品': 'semi'}
                db.session.add(Inventory(
                    project_id=project_id, inventory_date=datetime.utcnow().date(),
                    category=cat_map.get(str(cat), 'raw'), spec=spec,
                    piece_count=count, unit_weight=uw, total_weight=tw,
                    created_by=user_id,
                ))
                success += 1
        except:
            failed += 1
    db.session.commit()
    return success, failed


def import_waste(file_path, project_id, user_id):
    """导入废料台账"""
    df = pd.read_excel(file_path, header=None)
    success, failed = 0, 0
    for idx in range(2, len(df)):
        try:
            row = df.iloc[idx]
            date = parse_date(row.iloc[1]) if pd.notna(row.iloc[1]) else datetime.utcnow().date()
            before = float(row.iloc[4]) if pd.notna(row.iloc[4]) else 0
            after = float(row.iloc[5]) if pd.notna(row.iloc[5]) else 0
            weight = float(row.iloc[6]) if pd.notna(row.iloc[6]) else 0
            team = str(row.iloc[11]) if len(row) > 11 and pd.notna(row.iloc[11]) else ''
            if weight > 0:
                db.session.add(Waste(
                    project_id=project_id, process_date=date,
                    vehicle_before=before, vehicle_after=after,
                    waste_weight=weight, labor_team=team,
                    created_by=user_id,
                ))
                success += 1
        except:
            failed += 1
    db.session.commit()
    return success, failed


IMPORTERS = {
    'incoming': import_incoming,
    'transfer': import_transfer,
    'measure': import_measure,
    'inventory': import_inventory,
    'waste': import_waste,
}
