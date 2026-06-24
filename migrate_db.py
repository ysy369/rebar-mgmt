"""
数据库迁移脚本：添加 projects / user_projects 缺失列
用法: python migrate_db.py
"""
import pymysql

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "rebar",
    "password": "changeme",
    "database": "rebar_mgmt",
}

MIGRATIONS = [
    # (表名, 检查列, ALTER SQL, 描述)
    ("projects", "contract_name",
     'ALTER TABLE projects ADD COLUMN contract_name VARCHAR(300) NULL COMMENT "合同名称" AFTER name',
     "projects.contract_name"),
    ("projects", "start_date",
     'ALTER TABLE projects ADD COLUMN start_date DATE NULL COMMENT "开工日期" AFTER description',
     "projects.start_date"),
    ("projects", "duration_days",
     'ALTER TABLE projects ADD COLUMN duration_days INT NULL COMMENT "总工期(天)" AFTER start_date',
     "projects.duration_days"),
    ("projects", "building_area",
     'ALTER TABLE projects ADD COLUMN building_area DECIMAL(12,2) NULL COMMENT "建筑面积(m²)" AFTER duration_days',
     "projects.building_area"),
    ("projects", "rebar_content",
     'ALTER TABLE projects ADD COLUMN rebar_content DECIMAL(10,3) NULL COMMENT "钢筋含量(kg/m²)" AFTER building_area',
     "projects.rebar_content"),
    ("user_projects", "role",
     "ALTER TABLE user_projects ADD COLUMN role ENUM('engineer','reviewer','viewer') NOT NULL DEFAULT 'engineer' COMMENT '成员角色' AFTER project_id",
     "user_projects.role"),
]

def main():
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    print(f"已连接到数据库: {DB_CONFIG['database']}")
    print("-" * 50)

    for table, col, sql, desc in MIGRATIONS:
        cur.execute(f"SHOW COLUMNS FROM {table} LIKE '{col}'")
        if cur.fetchone():
            print(f"  ✅ {desc} — 已存在，跳过")
        else:
            cur.execute(sql)
            conn.commit()
            print(f"  🔧 {desc} — 已添加")

    conn.close()
    print("-" * 50)
    print("数据库迁移完成！请重启应用验证。")

if __name__ == "__main__":
    main()
