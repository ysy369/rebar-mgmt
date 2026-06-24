-- ============================================
-- 数据库迁移：补充 projects / user_projects 缺失列
-- 日期：2026-06-23
-- 执行方式：mysql -u rebar -p rebar_mgmt < 此文件
-- ============================================

-- projects 表新增字段
ALTER TABLE projects
    ADD COLUMN contract_name VARCHAR(300) NULL COMMENT '合同名称' AFTER name,
    ADD COLUMN start_date DATE NULL COMMENT '开工日期' AFTER description,
    ADD COLUMN duration_days INT NULL COMMENT '总工期(天)' AFTER start_date,
    ADD COLUMN building_area DECIMAL(12,2) NULL COMMENT '建筑面积(m²)' AFTER duration_days,
    ADD COLUMN rebar_content DECIMAL(10,3) NULL COMMENT '钢筋含量(kg/m²)' AFTER building_area;

-- user_projects 表新增角色字段
ALTER TABLE user_projects
    ADD COLUMN role ENUM('engineer', 'reviewer', 'viewer') NOT NULL DEFAULT 'engineer' COMMENT '成员角色' AFTER project_id;

-- 验证
DESCRIBE projects;
DESCRIBE user_projects;
