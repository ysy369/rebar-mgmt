# ============================================
# 钢筋精细化管理平台 — 模板展示用常量映射
# ============================================
"""
集中定义所有需要在模板中展示的状态/类型映射，
避免在多个 Jinja2 模板中重复定义字典。
"""

# ---------- 料单审核状态 ----------
CUTTING_ORDER_STATUS_MAP = {
    "draft": {"label": "草稿", "color": "secondary"},
    "submitted": {"label": "待审核", "color": "info"},
    "reviewed": {"label": "已审核", "color": "warning"},
    "approved": {"label": "已通过", "color": "success"},
    "rejected": {"label": "已驳回", "color": "danger"},
}

# ---------- BOM 构件类型 ----------
COMPONENT_TYPE_MAP = {
    "column": {"label": "柱", "color": "primary"},
    "beam": {"label": "梁", "color": "info"},
    "slab": {"label": "板", "color": "warning"},
    "wall": {"label": "墙", "color": "success"},
    "stair": {"label": "楼梯", "color": "danger"},
    "other": {"label": "其他", "color": "secondary"},
}

# ---------- BOM 施工状态 ----------
COMPONENT_STATUS_MAP = {
    "not_started": {"label": "未施工", "color": "secondary"},
    "in_progress": {"label": "正在施工", "color": "warning"},
    "poured": {"label": "已浇筑", "color": "success"},
}

# ---------- 形象进度状态 ----------
BUILDING_PROGRESS_STATUS_MAP = {
    "未施工": {"label": "未施工", "color": "secondary"},
    "施工中": {"label": "施工中", "color": "warning"},
    "已完成": {"label": "已完成", "color": "success"},
    "pending": {"label": "未施工", "color": "secondary"},
    "active": {"label": "施工中", "color": "warning"},
    "done": {"label": "已完成", "color": "success"},
}

# ---------- 调拨方向 ----------
TRANSFER_DIRECTION_MAP = {
    "in": {"label": "调入", "color": "success"},
    "out": {"label": "调出", "color": "warning"},
}

# ---------- 调拨类型 ----------
TRANSFER_TYPE_MAP = {
    "raw": {"label": "原材", "color": "info"},
    "semi": {"label": "半成品", "color": "primary"},
}

# ---------- 盘点类别 ----------
INVENTORY_CATEGORY_MAP = {
    "raw": {"label": "钢筋原材", "color": "info"},
    "short": {"label": "短料余头", "color": "warning"},
    "semi": {"label": "半成品", "color": "primary"},
    "total": {"label": "合计", "color": "secondary"},
}

# ---------- 措施筋类别 ----------
MEASURE_CATEGORY_MAP = {
    "budget": {"label": "预算内", "color": "primary"},
    "non_budget": {"label": "非预算", "color": "warning"},
}

# ---------- 项目成本类别 ----------
COST_CATEGORY_MAP = {
    "labor": {"label": "人工费", "color": "primary"},
    "material": {"label": "材料费", "color": "success"},
    "equipment": {"label": "机械费", "color": "info"},
    "transport": {"label": "运输费", "color": "warning"},
    "management": {"label": "管理费", "color": "secondary"},
    "other": {"label": "其他", "color": "dark"},
}

# ---------- 导入批次状态 ----------
IMPORT_BATCH_STATUS_MAP = {
    "pending": {"label": "待处理", "color": "secondary"},
    "processing": {"label": "处理中", "color": "info"},
    "done": {"label": "待审核", "color": "warning"},
    "failed": {"label": "失败", "color": "danger"},
    "approved": {"label": "已通过", "color": "success"},
    "rejected": {"label": "已驳回", "color": "danger"},
}

# ---------- 项目状态 ----------
PROJECT_STATUS_MAP = {
    "finished": {"label": "已完工", "color": "success"},
    "in_progress": {"label": "在建", "color": "primary"},
    "not_started": {"label": "未开工", "color": "secondary"},
    "stopped": {"label": "停工", "color": "warning"},
}

# ---------- 用户角色 ----------
USER_ROLE_MAP = {
    "admin": {"label": "管理员", "color": "warning"},
    "user": {"label": "工程师", "color": "info"},
}

# ---------- 用户账号状态 ----------
USER_STATUS_MAP = {
    True: {"label": "正常", "color": "success"},
    False: {"label": "已禁用", "color": "secondary"},
}

# ---------- 汇总到模板的全局字典 ----------
TEMPLATE_GLOBALS = {
    "CUTTING_ORDER_STATUS_MAP": CUTTING_ORDER_STATUS_MAP,
    "COMPONENT_TYPE_MAP": COMPONENT_TYPE_MAP,
    "COMPONENT_STATUS_MAP": COMPONENT_STATUS_MAP,
    "BUILDING_PROGRESS_STATUS_MAP": BUILDING_PROGRESS_STATUS_MAP,
    "TRANSFER_DIRECTION_MAP": TRANSFER_DIRECTION_MAP,
    "TRANSFER_TYPE_MAP": TRANSFER_TYPE_MAP,
    "INVENTORY_CATEGORY_MAP": INVENTORY_CATEGORY_MAP,
    "MEASURE_CATEGORY_MAP": MEASURE_CATEGORY_MAP,
    "COST_CATEGORY_MAP": COST_CATEGORY_MAP,
    "IMPORT_BATCH_STATUS_MAP": IMPORT_BATCH_STATUS_MAP,
    "PROJECT_STATUS_MAP": PROJECT_STATUS_MAP,
    "USER_ROLE_MAP": USER_ROLE_MAP,
    "USER_STATUS_MAP": USER_STATUS_MAP,
}

# ---------- 图表统一配色 ----------
CHART_COLORS = [
    "#1a2744",  # 主色深蓝（ink）
    "#f15a24",  # 强调钢筋橙
    "#0098ae",  # 信息青
    "#198754",  # 成功绿
    "#f0a020",  # 警告黄
    "#dc3545",  # 危险红
    "#6f42c1",  # 紫色
    "#20c997",  # 青色
]
