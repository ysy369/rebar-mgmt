import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import Flask, redirect, url_for, request, session, abort, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

logger = logging.getLogger(__name__)
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

login_manager.login_view = "auth.login"
login_manager.login_message = "请先登录后再访问该页面。"
login_manager.login_message_category = "warning"


def _build_period_options(months=24):
    """生成最近 N 个月的周期选项（YYYY-MM 格式）"""
    options = []
    now = datetime.utcnow()
    for i in range(months):
        d = now - timedelta(days=i * 30)
        value = d.strftime("%Y-%m")
        text = d.strftime("%Y年%m月")
        options.append((value, text))
    return options


def _format_number(value, precision=2):
    """通用数字格式化过滤器"""
    if value is None:
        value = 0
    try:
        return ("{:." + str(precision) + "f}").format(float(value))
    except (ValueError, TypeError):
        return value


def _format_ton(value, precision=3):
    return _format_number(value, precision)


def _format_kg(value, precision=1):
    return _format_number(value, precision)


def _format_money(value, precision=2):
    return _format_number(value, precision)


def _format_percent(value, precision=1):
    return _format_number(value, precision)


def _auto_migrate(app):
    """启动时自动添加缺失的数据库列（幂等操作，不阻塞启动）"""
    with app.app_context():
        try:
            from sqlalchemy import text, inspect
            inspector = inspect(db.engine)

            migrations = [
                ("projects", "contract_name",
                 "ALTER TABLE projects ADD COLUMN contract_name VARCHAR(300) NULL COMMENT '合同名称' AFTER name"),
                ("projects", "start_date",
                 "ALTER TABLE projects ADD COLUMN start_date DATE NULL COMMENT '开工日期' AFTER description"),
                ("projects", "duration_days",
                 "ALTER TABLE projects ADD COLUMN duration_days INT NULL COMMENT '总工期(天)' AFTER start_date"),
                ("projects", "building_area",
                 "ALTER TABLE projects ADD COLUMN building_area DECIMAL(12,2) NULL COMMENT '建筑面积(m²)' AFTER duration_days"),
                ("projects", "rebar_content",
                 "ALTER TABLE projects ADD COLUMN rebar_content DECIMAL(10,3) NULL COMMENT '钢筋含量(kg/m²)' AFTER building_area"),
                ("user_projects", "role",
                 "ALTER TABLE user_projects ADD COLUMN role ENUM('engineer','reviewer','viewer') NOT NULL DEFAULT 'engineer' COMMENT '成员角色' AFTER project_id"),
                ("projects", "contract_no",
                 "ALTER TABLE projects ADD COLUMN contract_no VARCHAR(100) NULL COMMENT '合同编号' AFTER contract_name"),
                ("projects", "project_name",
                 "ALTER TABLE projects ADD COLUMN project_name VARCHAR(255) NULL COMMENT '工程名称' AFTER contract_no"),
                ("projects", "total_contractor_name",
                 "ALTER TABLE projects ADD COLUMN total_contractor_name VARCHAR(255) NULL COMMENT '总包单位名称' AFTER project_name"),
                ("projects", "est_rebar_total",
                 "ALTER TABLE projects ADD COLUMN est_rebar_total DECIMAL(15,3) NULL COMMENT '预估钢筋总量(T)' AFTER duration_days"),
                ("projects", "project_location",
                 "ALTER TABLE projects ADD COLUMN project_location VARCHAR(500) NULL COMMENT '工程地点' AFTER rebar_content"),
                ("projects", "service_scope",
                 "ALTER TABLE projects ADD COLUMN service_scope TEXT NULL COMMENT '服务范围' AFTER project_location"),
                ("projects", "service_content",
                 "ALTER TABLE projects ADD COLUMN service_content TEXT NULL COMMENT '服务内容' AFTER service_scope"),
                ("projects", "service_duration",
                 "ALTER TABLE projects ADD COLUMN service_duration INT NULL COMMENT '服务工期(天)' AFTER service_content"),
                ("projects", "contract_amount",
                 "ALTER TABLE projects ADD COLUMN contract_amount DECIMAL(14,2) NULL COMMENT '合同额(万元)' AFTER service_duration"),
                ("projects", "output_value",
                 "ALTER TABLE projects ADD COLUMN output_value DECIMAL(14,2) NULL COMMENT '累计产值(万元)' AFTER contract_amount"),
                # ImportedFile 异步导入字段
                ("imported_files", "task_id",
                 "ALTER TABLE imported_files ADD COLUMN task_id VARCHAR(100) NULL COMMENT 'Celery任务ID' AFTER uploaded_at"),
                ("imported_files", "status",
                 "ALTER TABLE imported_files ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '导入状态' AFTER task_id"),
                ("imported_files", "progress",
                 "ALTER TABLE imported_files ADD COLUMN progress INT NOT NULL DEFAULT 0 COMMENT '进度0-100' AFTER status"),
                ("imported_files", "error_message",
                 "ALTER TABLE imported_files ADD COLUMN error_message TEXT NULL COMMENT '错误信息' AFTER progress"),
            ]

            with db.engine.connect() as conn:
                # 1. 添加缺失列
                for table, col, sql in migrations:
                    try:
                        result = conn.execute(
                            text("SELECT COUNT(*) FROM information_schema.COLUMNS "
                                 "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"),
                            {"t": table, "c": col}
                        )
                        exists = result.scalar() > 0
                        if not exists:
                            conn.execute(text(sql))
                            conn.commit()
                            logger.info(f"Auto-migration: added {table}.{col}")
                    except Exception as exc:
                        logger.warning(f"Auto-migration check {table}.{col}: {exc}")

                # 2. 将 projects.status 从 enum 改为 varchar(20) 以支持 4 种状态
                try:
                    col_info = conn.execute(
                        text("SELECT DATA_TYPE, COLUMN_TYPE FROM information_schema.COLUMNS "
                             "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects' AND COLUMN_NAME = 'status'")
                    ).first()
                    if col_info and col_info[0].lower() == "enum":
                        conn.execute(text(
                            "ALTER TABLE projects MODIFY COLUMN status VARCHAR(20) NOT NULL DEFAULT 'in_progress' COMMENT '项目状态'"
                        ))
                        conn.execute(text(
                            "UPDATE projects SET status = CASE status WHEN 'active' THEN 'in_progress' WHEN 'archived' THEN 'finished' ELSE status END"
                        ))
                        conn.commit()
                        logger.info("Auto-migration: converted projects.status to varchar(20) and mapped old values")
                except Exception as exc:
                    logger.warning(f"Auto-migration status conversion: {exc}")

                # 3. 创建 imported_files 表（如不存在）
                try:
                    table_exists = conn.execute(
                        text("SELECT COUNT(*) FROM information_schema.TABLES "
                             "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'imported_files'")
                    ).scalar() > 0
                    if not table_exists:
                        conn.execute(text("""
                            CREATE TABLE imported_files (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                project_id INT NOT NULL COMMENT '项目ID',
                                ledger_type ENUM('incoming','transfer','measure_rebar','fangyang_requisition','inventory','waste','progress','model_quantity','secondary','detailing','non_budget','pile_foundation','support_structure') NOT NULL COMMENT '台账类型',
                                original_filename VARCHAR(255) NOT NULL COMMENT '原始文件名',
                                file_path VARCHAR(500) NOT NULL COMMENT '存储路径',
                                file_size INT NULL COMMENT '文件大小(字节)',
                                uploaded_by INT NULL COMMENT '上传人ID',
                                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
                                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                                FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='导入文件表'
                        """))
                        conn.commit()
                        logger.info("Auto-migration: created imported_files table")
                    else:
                        # 3b. 已存在表时，检查并扩展 ledger_type 枚举
                        try:
                            col_info = conn.execute(
                                text("SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
                                     "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'imported_files' AND COLUMN_NAME = 'ledger_type'")
                            ).first()
                            if col_info and "'support_structure'" not in col_info[0]:
                                conn.execute(text(
                                    "ALTER TABLE imported_files MODIFY COLUMN ledger_type "
                                    "ENUM('incoming','transfer','measure_rebar','fangyang_requisition','inventory','waste','progress','model_quantity','secondary','detailing','non_budget','pile_foundation','support_structure') NOT NULL COMMENT '台账类型'"
                                ))
                                conn.commit()
                                logger.info("Auto-migration: extended imported_files.ledger_type enum")
                        except Exception as exc:
                            logger.warning(f"Auto-migration ledger_type enum extension: {exc}")
                except Exception as exc:
                    logger.warning(f"Auto-migration imported_files table: {exc}")

                # 4. 创建扩展台账表（如不存在）
                _extended_tables = {
                    "detailing_records": """
                        CREATE TABLE IF NOT EXISTS detailing_records (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            project_id INT NOT NULL COMMENT '项目ID',
                            imported_file_id INT NULL COMMENT '导入文件ID',
                            date DATE NULL COMMENT '日期',
                            spec VARCHAR(50) NULL COMMENT '规格型号',
                            weight_ton DECIMAL(10,3) NULL COMMENT '重量(吨)',
                            remark VARCHAR(200) NULL COMMENT '备注',
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            INDEX idx_detailing_project (project_id),
                            INDEX idx_detailing_date (date),
                            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                            FOREIGN KEY (imported_file_id) REFERENCES imported_files(id) ON DELETE SET NULL
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='钢筋翻样台账'
                    """,
                    "non_budget_records": """
                        CREATE TABLE IF NOT EXISTS non_budget_records (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            project_id INT NOT NULL COMMENT '项目ID',
                            imported_file_id INT NULL COMMENT '导入文件ID',
                            date DATE NULL COMMENT '日期',
                            spec VARCHAR(50) NULL COMMENT '规格型号',
                            weight_ton DECIMAL(10,3) NULL COMMENT '重量(吨)',
                            remark VARCHAR(200) NULL COMMENT '备注',
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            INDEX idx_non_budget_project (project_id),
                            INDEX idx_non_budget_date (date),
                            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                            FOREIGN KEY (imported_file_id) REFERENCES imported_files(id) ON DELETE SET NULL
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='非预算收入使用钢筋台账'
                    """,
                    "pile_foundation_records": """
                        CREATE TABLE IF NOT EXISTS pile_foundation_records (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            project_id INT NOT NULL COMMENT '项目ID',
                            imported_file_id INT NULL COMMENT '导入文件ID',
                            date DATE NULL COMMENT '日期',
                            spec VARCHAR(50) NULL COMMENT '规格型号',
                            weight_ton DECIMAL(10,3) NULL COMMENT '重量(吨)',
                            remark VARCHAR(200) NULL COMMENT '备注',
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            INDEX idx_pile_foundation_project (project_id),
                            INDEX idx_pile_foundation_date (date),
                            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                            FOREIGN KEY (imported_file_id) REFERENCES imported_files(id) ON DELETE SET NULL
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='主体桩基台账'
                    """,
                    "support_structure_records": """
                        CREATE TABLE IF NOT EXISTS support_structure_records (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            project_id INT NOT NULL COMMENT '项目ID',
                            imported_file_id INT NULL COMMENT '导入文件ID',
                            date DATE NULL COMMENT '日期',
                            spec VARCHAR(50) NULL COMMENT '规格型号',
                            weight_ton DECIMAL(10,3) NULL COMMENT '重量(吨)',
                            remark VARCHAR(200) NULL COMMENT '备注',
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            INDEX idx_support_structure_project (project_id),
                            INDEX idx_support_structure_date (date),
                            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                            FOREIGN KEY (imported_file_id) REFERENCES imported_files(id) ON DELETE SET NULL
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基坑支护台账'
                    """,
                }
                for tbl_name, create_sql in _extended_tables.items():
                    try:
                        tbl_exists = conn.execute(
                            text("SELECT COUNT(*) FROM information_schema.TABLES "
                                 "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"),
                            {"t": tbl_name}
                        ).scalar() > 0
                        if not tbl_exists:
                            conn.execute(text(create_sql))
                            conn.commit()
                            logger.info(f"Auto-migration: created table {tbl_name}")
                    except Exception as exc:
                        logger.warning(f"Auto-migration create {tbl_name}: {exc}")

        except Exception as exc:
            logger.warning(f"Auto-migration skipped (DB not ready?): {exc}")


def create_app(config_name=None):
    """Flask 应用工厂"""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    # 确保项目根目录在 sys.path 中（Celery Worker 子进程可能需要）
    import sys as _sys
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _project_root not in _sys.path:
        _sys.path.insert(0, _project_root)
    from config import config_map
    app.config.from_object(config_map.get(config_name, config_map["development"]))

    # Nginx 反向代理：信任 X-Forwarded-* 头
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # 初始化 Celery（注入 Flask 应用上下文）
    from app.celery_app import make_celery
    make_celery(app)

    # 自动执行数据库迁移（添加缺失列，幂等操作）
    _auto_migrate(app)

    # 注册模板全局变量（状态/类型映射）
    from app.services.constants import TEMPLATE_GLOBALS

    for key, value in TEMPLATE_GLOBALS.items():
        app.jinja_env.globals[key] = value

    # 注册常用 Python 内置函数到 Jinja2 全局命名空间
    app.jinja_env.globals["min"] = min
    app.jinja_env.globals["max"] = max
    app.jinja_env.globals["zip"] = zip

    # 注册模板过滤器
    app.jinja_env.filters["format_ton"] = _format_ton
    app.jinja_env.filters["format_kg"] = _format_kg
    app.jinja_env.filters["format_money"] = _format_money
    app.jinja_env.filters["format_percent"] = _format_percent

    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.project import project_bp
    from app.routes.api import api_bp
    from app.routes.bom import bom_bp
    from app.routes.ledger import ledger_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.settlement import settlement_bp
    from app.routes.home import home_bp
    from app.routes.labor import labor_bp
    from app.routes.audit import audit_bp
    from app.routes.site import site_bp
    from app.routes.work import work_bp
    from app.routes.system import system_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(project_bp, url_prefix="/project")
    app.register_blueprint(api_bp)
    app.register_blueprint(bom_bp, url_prefix="/bom")
    app.register_blueprint(ledger_bp, url_prefix="/ledger")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(settlement_bp, url_prefix="/settlement")
    app.register_blueprint(home_bp, url_prefix="/home")
    app.register_blueprint(labor_bp, url_prefix="/labor")
    app.register_blueprint(audit_bp, url_prefix="/audit")
    app.register_blueprint(site_bp, url_prefix="/site")
    app.register_blueprint(work_bp, url_prefix="/work")
    app.register_blueprint(system_bp, url_prefix="/system")

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("home.index"))
        return redirect(url_for("auth.login"))

    @app.route("/health")
    def health():
        """健康检查端点：供 Docker / 负载均衡 / 监控使用。"""
        checks = {}
        status_code = 200
        overall = "healthy"

        # 1. 数据库连接检查
        try:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"
            overall = "unhealthy"
            status_code = 503

        # 2. 上传/导出目录可写检查
        for folder_key, folder_path in (
            ("upload_folder", app.config["UPLOAD_FOLDER"]),
            ("export_folder", app.config["EXPORT_FOLDER"]),
        ):
            try:
                test_file = os.path.join(folder_path, ".health_write_test")
                with open(test_file, "w") as f:
                    f.write("ok")
                os.remove(test_file)
                checks[folder_key] = "ok"
            except Exception as exc:
                checks[folder_key] = f"error: {exc}"
                overall = "unhealthy"
                status_code = 503

        payload = {
            "status": overall,
            "service": "rebar-app",
            "version": app.config.get("APP_VERSION", "v1.0"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        }
        return jsonify(payload), status_code

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["EXPORT_FOLDER"], exist_ok=True)

    @app.before_request
    def csrf_protect():
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            # 登录请求可跳过 CSRF（用户尚未建立 session）
            if request.endpoint == "auth.login":
                return
            token = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")
            if not token or token != session.get("_csrf_token"):
                abort(400)

    @app.after_request
    def force_utf8(response):
        if "text/html" in response.content_type:
            response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response

    @app.context_processor
    def inject_globals():
        def gen_csrf():
            if "_csrf_token" not in session:
                session["_csrf_token"] = secrets.token_hex(32)
            return session["_csrf_token"]

        project = None
        if request.endpoint and request.endpoint.startswith(("project.", "ledger.", "bom.")):
            if request.view_args:
                project_id = request.view_args.get("project_id") or request.view_args.get("id")
                if project_id:
                    from app.models import Project
                    try:
                        project = Project.query.get(int(project_id))
                    except (ValueError, TypeError):
                        project = None

        from markupsafe import Markup
        token = gen_csrf()
        return {
            "APP_NAME": "钢筋精细化管理平台",
            "APP_VERSION": "v1.0",
            "csrf_token": token,
            "csrf_field": Markup(f'<input type="hidden" name="_csrf_token" value="{token}">'),
            "current_project": project,
            "period_options": _build_period_options(),
            "platform_type": session.get("platform_type", "jinguan"),
        }

    return app
