"""钢筋台账数据导入服务——Celery 异步解析 Excel"""
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import pandas as pd
from flask import current_app
from app import db
from app.models import Incoming, Transfer, MeasureRebar, Inventory, Waste, ImportedFile
from app.celery_app import celery

# Celery Worker 进程内缓存 Flask app（避免每次 task 重建）
_worker_app = None


def _get_worker_app():
    """获取或创建 Celery Worker 专用的 Flask 应用实例"""
    global _worker_app
    if _worker_app is None:
        from app import create_app
        _worker_app = create_app()
    return _worker_app

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


# ============================================================
# 核心解析函数（原 import_xxx → _do_parse_xxx，逻辑零改动）
# ============================================================

def _do_parse_incoming(file_path, project_id, user_id=None):
    """导入进场台账——匹配真实模板列"""
    df = pd.read_excel(file_path, header=None)
    success, failed = 0, 0
    for idx in range(3, len(df)):
        try:
            row = df.iloc[idx]
            seq = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
            if not seq.isdigit():
                continue
            date = parse_date(row.iloc[1])
            receipt = str(row.iloc[2]) if pd.notna(row.iloc[2]) else None
            brand = str(row.iloc[3]) if pd.notna(row.iloc[3]) else None
            product = str(row.iloc[4]) if pd.notna(row.iloc[4]) else None
            spec = str(row.iloc[5]) if pd.notna(row.iloc[5]) else ''
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
    return {'count': success, 'failed': failed}


def _do_parse_transfer(file_path, project_id, user_id=None):
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
    return {'count': success, 'failed': failed}


def _do_parse_measure(file_path, project_id, user_id=None):
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
    return {'count': success, 'failed': failed}


def _do_parse_inventory(file_path, project_id, user_id=None):
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
    return {'count': success, 'failed': failed}


def _do_parse_waste(file_path, project_id, user_id=None):
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
    return {'count': success, 'failed': failed}


# 路由 dtype → 数据库 ledger_type 映射
# （路由 URL 使用短名如 'measure'，数据库存储标准名 'measure_rebar'）
DTYPE_TO_LEDGER_TYPE = {
    'incoming': 'incoming',
    'transfer': 'transfer',
    'measure': 'measure_rebar',
    'inventory': 'inventory',
    'waste': 'waste',
    'detailing': 'detailing',
    'non_budget': 'non_budget',
    'pile_foundation': 'pile_foundation',
    'support_structure': 'support_structure',
}

# 解析函数映射（Celery Task 内部使用）
_PARSE_FUNCTIONS = {
    'incoming': _do_parse_incoming,
    'transfer': _do_parse_transfer,
    'measure': _do_parse_measure,
    'inventory': _do_parse_inventory,
    'waste': _do_parse_waste,
}

# 向后兼容：旧代码直接调用 import_xxx 仍可使用
import_incoming = _do_parse_incoming
import_transfer = _do_parse_transfer
import_measure = _do_parse_measure
import_inventory = _do_parse_inventory
import_waste = _do_parse_waste

IMPORTERS = {
    'incoming': import_incoming,
    'transfer': import_transfer,
    'measure': import_measure,
    'inventory': import_inventory,
    'waste': import_waste,
}

# ============================================================
# Celery 异步任务
# ============================================================

def _update_import_status(imported_file_id, status, progress=0, error_message=None):
    """更新 ImportedFile 记录的导入状态"""
    try:
        record = ImportedFile.query.get(imported_file_id)
        if record:
            record.status = status
            record.progress = progress
            if error_message:
                record.error_message = error_message
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新导入状态失败: {e}")


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def process_excel_import(self, project_id, file_path, dtype, imported_file_id, user_id=None):
    """
    Celery 异步导入任务：后台解析 Excel → 写入数据库 → 更新进度 → 触发分析重算
    """
    app = _get_worker_app()
    with app.app_context():
        return _do_process_excel_import(self, project_id, file_path, dtype, imported_file_id, user_id)


def _do_process_excel_import(self, project_id, file_path, dtype, imported_file_id, user_id):
    """实际执行导入逻辑（需要 Flask app context）"""
    try:
        _update_import_status(imported_file_id, 'processing', 0)
        self.update_state(state='PROGRESS', meta={'progress': 5})

        # 未提供模板的四类台账：仅保存文件，跳过解析
        if dtype in ['detailing', 'non_budget', 'pile_foundation', 'support_structure']:
            _update_import_status(imported_file_id, 'completed', 100)
            self.update_state(state='SUCCESS', meta={'progress': 100})
            return {
                'status': 'completed',
                'message': '该类型暂不支持解析，仅保存文件',
                'records_count': 0,
            }

        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        self.update_state(state='PROGRESS', meta={'progress': 10})

        # 根据 dtype 调用对应解析函数
        parse_fn = _PARSE_FUNCTIONS.get(dtype)
        if not parse_fn:
            raise ValueError(f"不支持的台账类型: {dtype}")

        self.update_state(state='PROGRESS', meta={'progress': 20})
        result = parse_fn(file_path, project_id, user_id)

        _update_import_status(imported_file_id, 'completed', 100)
        self.update_state(state='SUCCESS', meta={'progress': 100})

        # 导入后自动触发分析重算
        try:
            from app.services.analysis_service import recalc_project_analysis
            from app.services.pl_service import recompute_project_pl
            recalc_project_analysis(project_id)
            recompute_project_pl(project_id)
        except Exception as e:
            current_app.logger.warning(f"分析重算失败: {e}")

        return {
            'status': 'completed',
            'records_count': result.get('count', 0) if result else 0,
        }

    except FileNotFoundError:
        error_msg = f"文件不存在: {file_path}"
        _update_import_status(imported_file_id, 'failed', 0, error_msg)
        self.update_state(state='FAILURE', meta={'progress': 0, 'error': error_msg})
        return {'status': 'failed', 'error': error_msg}
    except Exception as exc:
        error_msg = str(exc)
        _update_import_status(imported_file_id, 'failed', 0, error_msg)
        if self.request.retries < self.max_retries:
            self.update_state(state='RETRY', meta={'progress': 0, 'error': error_msg})
            raise self.retry(exc=exc)
        self.update_state(state='FAILURE', meta={'progress': 0, 'error': error_msg})
        return {'status': 'failed', 'error': error_msg}
