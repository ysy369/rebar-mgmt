# ============================================
# 配料单批量导入服务
# ============================================
import re
import os
from datetime import datetime

import pandas as pd
from werkzeug.utils import secure_filename

from app import db
from app.models.bom import Building, Floor, Area, Component, RebarDetail, ImportBatch

# 钢筋直径列映射
DIAMETER_COLS = ["6", "8", "10", "12", "14", "16", "18", "20", "22", "25", "28", "32"]

# 构件类型中英文映射
COMPONENT_TYPE_MAP = {
    "柱": "column", "梁": "beam", "板": "slab", "墙": "wall", "楼梯": "stair", "其他": "other",
    "柱子": "column", "剪力墙": "wall",
}
COMPONENT_TYPE_CN = {v: k for k, v in COMPONENT_TYPE_MAP.items() if len(k) <= 2}

# 施工状态映射
STATUS_MAP = {"未施工": "not_started", "正在施工": "in_progress", "已浇筑": "poured"}
STATUS_CN = {"not_started": "未施工", "in_progress": "正在施工", "poured": "已浇筑"}

# 文件名解析正则
# 格式: "项目名 楼层 区域 构件类型.xlsx"
# 如: "跨建-CIC4#科研中心 第1层 C区 柱.xlsx"
FILENAME_PATTERN = re.compile(
    r"(.+?)\s+(\S+层)\s+(\S+区)\s*(柱|梁|板|墙|楼梯)?\.xlsx?$"
)

# 备用解析：更宽松的匹配
FILENAME_PATTERN_LOOSE = re.compile(
    r"(.+?)[\s_]+(\S+?层)[\s_]+(\S+?区)[\s_]*(柱|梁|板|墙|楼梯)?"
)


def parse_filename(filename: str) -> dict:
    """从文件名解析项目、楼层、区域、构件类型"""
    basename = os.path.splitext(filename)[0]
    result = {"project": "", "floor": "", "area": "", "component_type": "其他"}

    # 尝试精确匹配
    m = FILENAME_PATTERN.match(filename)
    if not m:
        m = FILENAME_PATTERN_LOOSE.match(basename)

    if m:
        result["project"] = m.group(1).strip()
        result["floor"] = m.group(2).strip()
        result["area"] = m.group(3).strip()
        if m.group(4):
            result["component_type"] = m.group(4)
    else:
        # 无法解析时，尝试按空格分割
        parts = basename.replace("_", " ").split()
        if len(parts) >= 2:
            result["project"] = parts[0]
        if len(parts) >= 3:
            result["floor"] = parts[1] if "层" in parts[1] else parts[1] + "层"
        if len(parts) >= 4:
            result["area"] = parts[2] if "区" in parts[2] else parts[2] + "区"

    return result


def get_or_create_hierarchy(project_id: int, building_name: str = None,
                            floor_name: str = None, area_name: str = None):
    """获取或创建楼栋→楼层→区域层级"""
    building_name = building_name or "默认楼栋"
    floor_name = floor_name or "默认楼层"
    area_name = area_name or "默认区域"

    # Building
    building = Building.query.filter_by(project_id=project_id, name=building_name).first()
    if not building:
        building = Building(project_id=project_id, name=building_name)
        db.session.add(building)
        db.session.flush()

    # Floor
    floor = Floor.query.filter_by(building_id=building.id, name=floor_name).first()
    if not floor:
        floor = Floor(building_id=building.id, name=floor_name, sort_order=0)
        db.session.add(floor)
        db.session.flush()

    # Area
    area = Area.query.filter_by(floor_id=floor.id, name=area_name).first()
    if not area:
        area = Area(floor_id=floor.id, name=area_name)
        db.session.add(area)
        db.session.flush()

    return {"building": building, "floor": floor, "area": area}


def parse_excel_to_rebar(file_path: str, filename: str,
                         project_id: int, batch_id: int) -> dict:
    """解析单个 Excel 文件，提取钢筋数据"""
    result = {"success": 0, "failed": 0, "errors": [], "components_created": 0}

    try:
        info = parse_filename(filename)
        hierarchy = get_or_create_hierarchy(
            project_id,
            building_name=info.get("project"),
            floor_name=info.get("floor"),
            area_name=info.get("area"),
        )

        # 读取 Excel
        df = pd.read_excel(file_path, header=None)

        # 找表头行（含"直径"或"规格"的行）
        header_row = None
        for i in range(min(20, len(df))):
            row_values = [str(v).strip() for v in df.iloc[i].values if str(v) != "nan"]
            if any(kw in "".join(row_values) for kw in ["直径", "规格", "钢筋"]):
                header_row = i
                break

        if header_row is None:
            # 没有明显表头，用第一行作为表头
            header_row = 0

        # 提取表头
        headers = [str(df.iloc[header_row, j]).strip() if j < len(df.columns) else ""
                   for j in range(len(df.columns))]

        # 找直径列
        dia_col_map = {}
        for j, h in enumerate(headers):
            for dia in DIAMETER_COLS:
                if dia == h or dia in str(h):
                    dia_col_map[dia] = j
                    break

        if not dia_col_map:
            # 尝试用列号匹配（常见: B列=6, C列=8, ...）
            for j in range(1, min(20, len(df.columns))):
                val = str(df.iloc[header_row, j]).strip() if header_row < len(df) else ""
                if val.isdigit() and val in DIAMETER_COLS:
                    dia_col_map[val] = j

        # 找构件名列（通常在A列）
        name_col = 0

        # 解析数据行
        for row_idx in range(header_row + 1, len(df)):
            try:
                component_name = str(df.iloc[row_idx, name_col]).strip()
                if not component_name or component_name == "nan":
                    continue

                # 创建构件
                comp_type_raw = info.get("component_type", "其他")
                comp_type = COMPONENT_TYPE_MAP.get(comp_type_raw, "other")
                comp = Component(
                    area_id=hierarchy["area"].id,
                    name=component_name,
                    component_type=comp_type,
                    status="not_started",
                )
                db.session.add(comp)
                db.session.flush()
                result["components_created"] += 1

                # 提取各直径的重量
                has_data = False
                for dia, col_idx in dia_col_map.items():
                    try:
                        weight = df.iloc[row_idx, col_idx]
                        weight = float(weight) if pd.notna(weight) else 0
                        if weight > 0:
                            rd = RebarDetail(
                                component_id=comp.id,
                                diameter=int(dia),
                                weight=round(weight, 3),
                                source_file=filename,
                                batch_id=batch_id,
                            )
                            db.session.add(rd)
                            has_data = True
                    except (ValueError, TypeError):
                        pass

                if not has_data:
                    # 没有直径分列数据，尝试找总重量列
                    db.session.delete(comp)
                    result["components_created"] -= 1
                else:
                    result["success"] += 1

            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"行{row_idx+1}: {str(e)}")

    except Exception as e:
        result["failed"] += 1
        result["errors"].append(f"文件解析失败: {str(e)}")
        raise

    return result


def process_upload_batch(project_id: int, files: list, user_id: int = None) -> dict:
    """批量处理上传的 Excel 文件"""
    batch = ImportBatch(
        file_name=f"批量导入_{len(files)}个文件",
        project_id=project_id,
        status="processing",
        total_rows=len(files),
        created_by=user_id,
    )
    db.session.add(batch)
    db.session.flush()

    total_success = 0
    total_failed = 0
    all_errors = []

    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "bom")
    os.makedirs(upload_dir, exist_ok=True)

    source_paths = []

    ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}
    for file in files:
        if not file.filename:
            continue
        # 验证文件类型
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            total_failed += 1
            all_errors.append(f"{file.filename}: 不支持的文件类型，仅允许 .xlsx/.xls")
            continue
        try:
            safe_name = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            file_path = os.path.join(upload_dir, f"{timestamp}_{safe_name}")
            file.save(file_path)
            source_paths.append(file_path)

            result = parse_excel_to_rebar(file_path, file.filename, project_id, batch.id)
            total_success += result["success"]
            total_failed += result["failed"]
            all_errors.extend(result["errors"])

            db.session.commit()
        except Exception as e:
            total_failed += 1
            all_errors.append(f"{file.filename}: {str(e)}")
            db.session.rollback()

    batch.status = "done"
    batch.imported_count = total_success
    batch.failed_count = total_failed
    batch.error_detail = all_errors[:50] if all_errors else None
    batch.source_path = ",".join(source_paths) if source_paths else None
    db.session.commit()

    return {
        "batch_id": batch.id,
        "success": total_success,
        "failed": total_failed,
        "errors": all_errors[:20],
    }
