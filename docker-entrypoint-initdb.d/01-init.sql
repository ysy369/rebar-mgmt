-- ============================================
-- 钢筋精细化管理平台 — 数据库初始化
-- v2.0 基于真实 Excel 模板结构，Docker 首次启动自动执行
-- ============================================
SET NAMES utf8mb4;
SET GLOBAL time_zone = '+08:00';

-- ==================== 基础表 ====================

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(50) NOT NULL,
    role ENUM('admin', 'user') NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS client_units (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE COMMENT '甲方单位名称',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '项目名称（按合同名称写）',
    contract_name VARCHAR(300) NULL COMMENT '合同名称',
    client_unit_id INT NULL,
    contractor_id INT NULL COMMENT '承接公司ID',
    description TEXT NULL,
    start_date DATE NULL COMMENT '开工日期',
    duration_days INT NULL COMMENT '总工期(天)',
    building_area DECIMAL(12,2) NULL COMMENT '建筑面积(m²)',
    rebar_content DECIMAL(10,3) NULL COMMENT '钢筋含量(kg/m²)',
    status ENUM('active', 'archived') DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (client_unit_id) REFERENCES client_units(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    project_id INT NOT NULL,
    role ENUM('engineer', 'reviewer', 'viewer') NOT NULL DEFAULT 'engineer' COMMENT '成员角色',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_project (user_id, project_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 六大核心数据表 ====================

-- 1. 进场量（表1钢筋进场台账 / 表3进场量）
CREATE TABLE IF NOT EXISTS incoming (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    date DATE NOT NULL COMMENT '进场日期',
    receipt_no VARCHAR(100) NULL COMMENT '收料单号',
    brand VARCHAR(100) NULL COMMENT '品牌（如桂万钢）',
    product_name VARCHAR(100) NULL COMMENT '品名（如螺纹钢）',
    spec VARCHAR(100) NOT NULL COMMENT '规格（HRB400E/HPB300等）',
    material VARCHAR(50) NULL COMMENT '材质',
    rebar_length DECIMAL(6,1) NULL COMMENT '型号m（9米/12米）',
    piece_count INT NULL COMMENT '件数',
    theory_weight DECIMAL(12,3) NULL COMMENT '理论重量(T)',
    weigh_weight DECIMAL(12,3) NULL COMMENT '过磅后钢筋重量③=①-②(T)',
    vehicle_gross DECIMAL(12,3) NULL COMMENT '过磅重量车+钢筋①(T)',
    vehicle_tare DECIMAL(12,3) NULL COMMENT '过磅后车重量②(T)',
    plate_no VARCHAR(20) NULL COMMENT '车牌号',
    use_location VARCHAR(200) NULL COMMENT '使用部位',
    labor_team VARCHAR(200) NULL COMMENT '使用劳务队',
    remark TEXT NULL COMMENT '备注',
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 调拨量（表6调拨确认单：原材+半成品）
CREATE TABLE IF NOT EXISTS transfer (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL COMMENT '调出项目ID',
    date DATE NOT NULL COMMENT '调拨日期',
    transfer_type ENUM('raw', 'semi') NOT NULL DEFAULT 'raw' COMMENT '原材/半成品',
    direction ENUM('in', 'out') NOT NULL DEFAULT 'out' COMMENT '调拨方向',
    to_project VARCHAR(200) NULL COMMENT '调入接收项目名称',
    spec VARCHAR(100) NULL COMMENT '规格（原材用）',
    component_name VARCHAR(200) NULL COMMENT '构件名称（半成品用）',
    steel_diameter VARCHAR(50) NULL COMMENT '级别直径（半成品用）',
    rebar_sketch VARCHAR(500) NULL COMMENT '钢筋简图mm或计算式',
    cut_length DECIMAL(8,1) NULL COMMENT '下料mm',
    piece_count INT NULL COMMENT '根数/件数',
    total_pieces INT NULL COMMENT '总根数',
    weight DECIMAL(12,3) NOT NULL COMMENT '重量(T或kg)',
    remark TEXT NULL,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 措施筋（表2措施量 / 措施筋台账）
CREATE TABLE IF NOT EXISTS measure_rebar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    date DATE NOT NULL COMMENT '日期',
    seq_no VARCHAR(50) NULL COMMENT '编号',
    unit_name VARCHAR(200) NULL COMMENT '使用单位',
    work_type VARCHAR(100) NULL COMMENT '使用工种',
    use_location VARCHAR(200) NULL COMMENT '使用部位',
    usage_purpose VARCHAR(200) NULL COMMENT '用途（垫铁/马凳筋/梯子筋等）',
    spec_hrb400 VARCHAR(100) NULL COMMENT '规格型号HRB400',
    spec_hpb300 VARCHAR(100) NULL COMMENT '规格型号HPB300',
    weight_kg DECIMAL(12,3) NOT NULL COMMENT '重量(kg)',
    category ENUM('budget', 'non_budget') DEFAULT 'non_budget' COMMENT '预算内/非预算收入',
    non_budget_type VARCHAR(100) NULL COMMENT '非预算类型（塔吊基础/马凳筋/临建/降水井…）',
    signer_name VARCHAR(50) NULL COMMENT '项目签单人',
    signer_title VARCHAR(50) NULL COMMENT '签单人职务',
    labor_leader VARCHAR(50) NULL COMMENT '劳务班组组长',
    remark TEXT NULL,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 盘点量/剩余量（表4剩余量 / 钢筋盘点表）
CREATE TABLE IF NOT EXISTS inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    inventory_date DATE NOT NULL COMMENT '盘点日期',
    category ENUM('raw', 'short', 'semi', 'total') NOT NULL COMMENT '原材/短料余头/半成品/合计',
    spec VARCHAR(100) NOT NULL COMMENT '规格',
    piece_count INT NULL COMMENT '数量(件)',
    unit_weight DECIMAL(12,3) NULL COMMENT '单位重量(吨)',
    total_weight DECIMAL(12,3) NOT NULL COMMENT '合计重量(吨)',
    remark TEXT NULL,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 废料量（表5废料量 / 废料处理台账）
CREATE TABLE IF NOT EXISTS waste (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    process_date DATE NOT NULL COMMENT '处理日期',
    receipt_no VARCHAR(100) NULL COMMENT '单号',
    vehicle_before DECIMAL(10,3) NULL COMMENT '过磅前车重量(t)',
    vehicle_after DECIMAL(10,3) NULL COMMENT '过磅后车重量(t)',
    waste_weight DECIMAL(12,3) NOT NULL COMMENT '废料重量(T)（= 过磅前-过磅后）',
    rebar_length DECIMAL(6,1) NULL COMMENT '型号(m)',
    labor_team VARCHAR(200) NULL COMMENT '劳务队',
    plate_no VARCHAR(20) NULL COMMENT '车牌号',
    remark TEXT NULL,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 模型量/主体结构量（表1模型量）
CREATE TABLE IF NOT EXISTS model_quantity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    record_date DATE NOT NULL COMMENT '记录日期',
    spec VARCHAR(100) NOT NULL COMMENT '规格',
    structural_weight DECIMAL(12,3) NOT NULL COMMENT '主体结构量(T) ①',
    secondary_weight DECIMAL(12,3) NULL COMMENT '二构量(T) ④',
    remark TEXT NULL,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 汇总分析表 ====================

CREATE TABLE IF NOT EXISTS project_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL UNIQUE COMMENT '按项目唯一',
    period_start DATE NULL COMMENT '统计周期开始',
    period_end DATE NULL COMMENT '统计周期结束',
    -- 收入维度
    struct_qty DECIMAL(14,3) DEFAULT 0 COMMENT '①主体结构量(T)',
    measure_qty DECIMAL(14,3) DEFAULT 0 COMMENT '②措施筋(T)',
    non_entity_qty DECIMAL(14,3) DEFAULT 0 COMMENT '③非实体量(T)',
    sec_struct_qty DECIMAL(14,3) DEFAULT 0 COMMENT '④二构量(T)',
    budget_qty DECIMAL(14,3) DEFAULT 0 COMMENT '⑤=①+②+③-④ 施工图预算量(T)',
    contract_qty DECIMAL(14,3) DEFAULT 0 COMMENT '①对甲结算量(T)',
    -- 使用维度
    incoming_qty DECIMAL(14,3) DEFAULT 0 COMMENT '⑥进场量(T)',
    remaining_qty DECIMAL(14,3) DEFAULT 0 COMMENT '⑦剩余量(T)',
    waste_qty DECIMAL(14,3) DEFAULT 0 COMMENT '⑧废料量(T)',
    const_sec_qty DECIMAL(14,3) DEFAULT 0 COMMENT '⑨已施工二构量(T)',
    transfer_qty DECIMAL(14,3) DEFAULT 0 COMMENT '⑩调拨量(T)',
    non_budget_use_qty DECIMAL(14,3) DEFAULT 0 COMMENT '非预算收入使用量(T)',
    temp_facility_qty DECIMAL(14,3) DEFAULT 0 COMMENT '临建设施使用量(T)',
    usage_qty DECIMAL(14,3) DEFAULT 0 COMMENT '⑪=⑥-⑦-⑧-⑨-⑩ 使用量(T)',
    -- 结果
    saved_qty DECIMAL(14,3) DEFAULT 0 COMMENT '⑫=⑤-⑪ 节约量(T)',
    balance_rate DECIMAL(8,2) NULL COMMENT '⑬=⑫/⑤*100 结余率(%)',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 辅助表 ====================

CREATE TABLE IF NOT EXISTS import_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NULL,
    data_type VARCHAR(50) NOT NULL COMMENT 'incoming/transfer/measure_rebar/inventory/waste/model_quantity',
    file_name VARCHAR(255) NOT NULL,
    total_rows INT NOT NULL DEFAULT 0,
    success_rows INT NOT NULL DEFAULT 0,
    error_rows INT NOT NULL DEFAULT 0,
    error_detail JSON NULL,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS operation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(100) NOT NULL,
    target VARCHAR(200) NULL,
    detail JSON NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 索引 ====================
CREATE INDEX idx_incoming_project_date ON incoming(project_id, date);
CREATE INDEX idx_transfer_project_date ON transfer(project_id, date);
CREATE INDEX idx_measure_rebar_project_date ON measure_rebar(project_id, date);
CREATE INDEX idx_inventory_project_date ON inventory(project_id, inventory_date);
CREATE INDEX idx_waste_project_date ON waste(project_id, process_date);
CREATE INDEX idx_model_qty_project_date ON model_quantity(project_id, record_date);
CREATE INDEX idx_import_logs_project ON import_logs(project_id, created_at);
CREATE INDEX idx_user_projects_user ON user_projects(user_id);

-- ==================== 视图：项目汇总 ====================
CREATE OR REPLACE VIEW v_project_summary AS
SELECT
    p.id AS project_id,
    p.name AS project_name,
    cu.name AS client_unit,
    pa.balance_rate,
    pa.budget_qty,
    pa.usage_qty,
    pa.saved_qty,
    pa.incoming_qty,
    pa.transfer_qty,
    pa.waste_qty,
    pa.remaining_qty
FROM projects p
LEFT JOIN client_units cu ON p.client_unit_id = cu.id
LEFT JOIN project_analysis pa ON p.id = pa.project_id;

-- ==================== 业务扩展表（v3.0） ====================

-- 承接公司
CREATE TABLE IF NOT EXISTS contractors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE COMMENT '承接公司名称',
    contact_person VARCHAR(100) NULL COMMENT '联系人',
    contact_phone VARCHAR(50) NULL COMMENT '联系电话',
    address VARCHAR(500) NULL COMMENT '地址',
    remark TEXT NULL COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 项目附件/效果图
CREATE TABLE IF NOT EXISTS project_attachments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    attachment_type ENUM('rendering','document','other') DEFAULT 'rendering',
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INT NULL,
    mime_type VARCHAR(100) NULL,
    description VARCHAR(500) NULL,
    sort_order INT DEFAULT 0,
    is_cover TINYINT(1) DEFAULT 0,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_pa_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 料单审核台账（主表）
CREATE TABLE IF NOT EXISTS cutting_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    order_no VARCHAR(100) NOT NULL,
    order_date DATE NOT NULL,
    batch_no VARCHAR(100) NULL,
    labor_team VARCHAR(200) NULL,
    use_location VARCHAR(500) NULL,
    total_pieces INT NULL,
    total_weight DECIMAL(12,3) NULL,
    status ENUM('draft','submitted','reviewed','approved','rejected') DEFAULT 'draft',
    submitted_by INT NULL,
    submitted_at DATETIME NULL,
    reviewed_by INT NULL,
    reviewed_at DATETIME NULL,
    review_comment TEXT NULL,
    remark TEXT NULL,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (submitted_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_co_project_status (project_id, status),
    INDEX idx_co_order_date (order_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 料单明细（子表）
CREATE TABLE IF NOT EXISTS cutting_order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    line_no INT NOT NULL,
    spec VARCHAR(100) NOT NULL,
    rebar_diameter VARCHAR(50) NULL,
    cut_length DECIMAL(8,1) NULL,
    piece_count INT NULL,
    unit_weight DECIMAL(12,3) NULL,
    total_weight DECIMAL(12,3) NULL,
    rebar_shape VARCHAR(500) NULL,
    component_name VARCHAR(200) NULL,
    remark TEXT NULL,
    FOREIGN KEY (order_id) REFERENCES cutting_orders(id) ON DELETE CASCADE,
    INDEX idx_coi_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 项目成本
CREATE TABLE IF NOT EXISTS project_costs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    cost_date DATE NOT NULL,
    cost_category ENUM('labor','material','equipment','transport','management','other') NOT NULL,
    cost_item VARCHAR(200) NOT NULL,
    amount DECIMAL(14,2) NOT NULL,
    description TEXT NULL,
    receipt_no VARCHAR(100) NULL,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_pc_project_date (project_id, cost_date),
    INDEX idx_pc_category (cost_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 项目盈亏
CREATE TABLE IF NOT EXISTS project_profit_loss (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL UNIQUE,
    rebar_unit_price DECIMAL(10,2) NOT NULL DEFAULT 5000,
    rebar_saved_qty DECIMAL(14,3) DEFAULT 0,
    rebar_income DECIMAL(14,2) DEFAULT 0,
    other_income DECIMAL(14,2) DEFAULT 0,
    total_income DECIMAL(14,2) DEFAULT 0,
    total_cost DECIMAL(14,2) DEFAULT 0,
    net_profit DECIMAL(14,2) DEFAULT 0,
    profit_rate DECIMAL(8,2) NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 配料单(BOM)相关表 ====================

-- 楼栋
CREATE TABLE IF NOT EXISTS buildings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    name VARCHAR(200) NOT NULL COMMENT '楼栋名称',
    INDEX idx_building_project (project_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 楼层
CREATE TABLE IF NOT EXISTS floors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    building_id INT NOT NULL,
    name VARCHAR(100) NOT NULL COMMENT '楼层名称',
    sort_order INT DEFAULT 0 COMMENT '排序',
    INDEX idx_floor_building (building_id),
    FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 区域
CREATE TABLE IF NOT EXISTS areas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    floor_id INT NOT NULL,
    name VARCHAR(100) NOT NULL COMMENT '区域名称',
    INDEX idx_area_floor (floor_id),
    FOREIGN KEY (floor_id) REFERENCES floors(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 构件
CREATE TABLE IF NOT EXISTS components (
    id INT AUTO_INCREMENT PRIMARY KEY,
    area_id INT NOT NULL,
    name VARCHAR(200) NOT NULL COMMENT '构件名称',
    component_type ENUM('column','beam','slab','wall','stair','other') NOT NULL DEFAULT 'other' COMMENT '构件类型',
    status ENUM('not_started','in_progress','poured') NOT NULL DEFAULT 'not_started' COMMENT '施工状态',
    INDEX idx_component_area (area_id),
    INDEX idx_component_status (status),
    FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 钢筋明细
CREATE TABLE IF NOT EXISTS rebar_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    component_id INT NOT NULL,
    diameter INT NOT NULL COMMENT '钢筋直径(mm)',
    weight DECIMAL(10,3) NOT NULL DEFAULT 0 COMMENT '重量(吨)',
    rebar_count INT NULL COMMENT '根数',
    single_length DECIMAL(8,2) NULL COMMENT '单根长度(m)',
    total_length DECIMAL(10,2) NULL COMMENT '总长度(m)',
    source_file VARCHAR(500) NULL COMMENT '来源文件名',
    batch_id INT NULL COMMENT '导入批次ID',
    remark TEXT NULL,
    INDEX idx_rd_component (component_id),
    INDEX idx_rd_batch (batch_id),
    FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 导入批次
CREATE TABLE IF NOT EXISTS import_batches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_name VARCHAR(500) NOT NULL COMMENT '文件名',
    project_id INT NOT NULL,
    status ENUM('pending','processing','done','failed','approved','rejected') NOT NULL DEFAULT 'pending' COMMENT '状态',
    reviewed_by INT NULL,
    reviewed_at DATETIME NULL COMMENT '审核时间',
    review_comment TEXT NULL COMMENT '审核意见',
    imported_count INT DEFAULT 0 COMMENT '成功导入条数',
    failed_count INT DEFAULT 0 COMMENT '失败条数',
    total_rows INT DEFAULT 0 COMMENT '总行数',
    error_detail JSON NULL COMMENT '错误详情',
    source_path VARCHAR(500) NULL COMMENT '源文件存储路径',
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ib_project (project_id, created_at),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 形象进度
CREATE TABLE IF NOT EXISTS building_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    building_name VARCHAR(200) NOT NULL COMMENT '楼栋名称',
    floor_name VARCHAR(100) NULL COMMENT '楼层',
    component_type VARCHAR(100) NULL COMMENT '构件类型',
    progress_status ENUM('未施工','施工中','已完成') DEFAULT '未施工',
    model_total DECIMAL(14,3) DEFAULT 0 COMMENT '模型总量(kg)',
    progress_qty DECIMAL(14,3) DEFAULT 0 COMMENT '进度量(kg)',
    total_weight DECIMAL(14,3) DEFAULT 0 COMMENT '钢筋总重(kg)',
    record_date DATE NULL,
    remark TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_bp_project (project_id),
    INDEX idx_bp_building (building_name),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 默认账号（admin / admin123 ; user1 / user123） ====================

-- projects 表补充外键（contractors 表在上方已创建）
ALTER TABLE projects ADD FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE SET NULL;

INSERT INTO users (username, password_hash, display_name, role) VALUES
('admin', '$2b$12$gW4VBdUS5RQbiSD25GNBi.TCp9.rIcFDO0CyYveyWnjwhq7XUw0ZO', '系统管理员', 'admin'),
('user1', '$2b$12$eTONAVs/YVEV3hJFsSSR..HYpHmhT0bgIqK64eIiGaOnhdcRclIvu', '精管工程师甲', 'user');
