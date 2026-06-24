# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 一、项目概述

| 项目 | 说明 |
|------|------|
| **项目名称** | 钢筋精细化管理平台 (Rebar Fine Management Platform) |
| **架构** | B/S 架构，Flask 工厂模式 + Jinja2 模板 |
| **部署** | Docker Compose（waitress 生产服务器），目标云服务器 `8.156.91.97` |
| **GitHub** | `git@github.com:ysy369/rebar-mgmt.git` |
| **后端** | Python 3.11 + Flask 3.1 |
| **数据库** | MySQL 8.0（SQLAlchemy ORM + Flask-Migrate + 启动时自动迁移） |
| **前端** | Bootstrap 5.3 + Chart.js 4.4 + Bootstrap Icons（全部 CDN，无构建工具） |
| **Excel** | openpyxl + pandas |

## 二、用户角色

| 角色 | 权限 |
|------|------|
| **管理员 (admin)** | 全部项目数据、导入、系统配置、跨项目对比 |
| **普通用户 (user)** | 仅操作被授权的项目，数据按项目严格隔离 |

---

## 三、Blueprint 架构（15 个模块）

| 文件 | Blueprint | url_prefix | 职责 |
|------|-----------|------------|------|
| `app/routes/home.py` | `home_bp` | `/home` | 首页：筛选 + KPI + 工作台 + 管理模块 + 图表 |
| `app/routes/project.py` | `project_bp` | `/project` | 项目详情 / 看板 / 导入 / 11 种台账表查看 |
| `app/routes/dashboard.py` | `dashboard_bp` | *(无)* | 深色科技数据看板；被 project.py 导入复用计算函数 |
| `app/routes/labor.py` | `labor_bp` | `/labor` | 劳务分包管理（独立全屏深色页面） |
| `app/routes/audit.py` | `audit_bp` | `/audit` | 盈亏分析 / 数据动态 / 采购计划 / 对比测算 |
| `app/routes/site.py` | `site_bp` | `/site` | 形象进度 / 物资领用 / 巡检 / 钢筋代换 / 优化台账 |
| `app/routes/work.py` | `work_bp` | `/work` | 工作管理 |
| `app/routes/system.py` | `system_bp` | `/system` | 用户管理 |
| `app/routes/admin.py` | `admin_bp` | `/admin` | 甲方单位 / 承接公司 / 项目 CRUD / 料单审核 |
| `app/routes/bom.py` | `bom_bp` | `/bom` | 配料单：导入→楼栋→楼层→区域→构件→钢筋明细树 |
| `app/routes/ledger.py` | `ledger_bp` | `/ledger` | 六大台账统一导入端点 |
| `app/routes/settlement.py` | `settlement_bp` | `/settlement` | 结算管理 |
| `app/routes/api.py` | `api_bp` | *(无)* | JSON API（级联下拉等） |
| `app/routes/auth.py` | `auth_bp` | `/auth` | 登录 / 登出 |

---

## 四、关键架构模式（非显而易见）

### 4.1 启动时自动迁移 `_auto_migrate()`
- 在 `create_app()` 中调用，**独立于 Flask-Migrate**
- 通过 `information_schema` 检查列是否存在，幂等添加缺失列
- 自动创建 `imported_files` 表并扩展其 `ledger_type` 枚举
- **新增字段只需在 `_auto_migrate()` 中添加一条迁移记录即可**——无需手动 SQL

### 4.2 CSRF 防护（双层机制）
- **服务端**：`before_request` 拦截 POST/PUT/DELETE/PATCH，验证 `session["_csrf_token"]`，登录端点跳过
- **客户端**：`app.js` 自动从 `<meta name="csrf-token">` 读取 token，注入所有 POST 表单隐藏域
- **模板中直接用 `{{ csrf_field|safe }}` 或什么都不写**——JS 会自动注入

### 4.3 模板上下文自动注入
`context_processor` (`inject_globals`) 向所有模板注入：
- `csrf_token`、`csrf_field`（已渲染的隐藏 input）
- `current_project` — 当路由以 `project.`/`ledger.`/`bom.` 开头时自动从 `view_args` 解析
- `period_options` — 最近 24 个月的 YYYY-MM 下拉选项
- `APP_NAME`、`APP_VERSION`

### 4.4 模板全局变量（来自 `app/services/constants.py`）
15 个 `*_MAP` 字典注入所有模板：`PROJECT_STATUS_MAP`、`CUTTING_ORDER_STATUS_MAP`、`COMPONENT_TYPE_MAP`、`TRANSFER_DIRECTION_MAP` 等。配合 `status_badge()` 宏使用。

### 4.5 模板过滤器
`|format_ton(1)` → 保留 1 位小数的吨数（默认 3 位）、`|format_kg`、`|format_money`、`|format_percent`

### 4.6 双主题模式
- **亮色标准**：继承 `base.html`，侧边栏 + 顶栏布局，用于管理后台页面
- **深色科技**：**独立 HTML 文档**，不继承 `base.html`，直接加载 CDN 资源，用于大屏看板（`dashboard/index.html`、`labor/fullscreen.html`）。配色：`#0a1628` 背景 + `#00d4ff` 青色 + `#ff7a00` 橙色

### 4.7 宏系统（`_macros.html`）
15 个可复用宏：`stat_card`、`status_badge`、`data_table`、`empty_state`、`render_pagination`、`chart_card`、`confirm_delete_form`、`render_breadcrumb`、`render_sidebar_menus`、`page_header`、`filter_reset_button`、`card_table`、`period_select`、`unit_select`、`stat_card_small`

### 4.8 菜单系统
- `base.html` 中硬编码 8 个一级菜单，通过 `data-menu-key` + JS `toggleMenu()` 展开/折叠
- 展开状态持久化到 `localStorage`（键：`expandedMenus_{context}_{projectId}`）
- 高亮：一级菜单对比 `request.endpoint`，子菜单通过 `active_menu` 变量

### 4.9 图表封装（`charts.js`）
`window.RebarCharts` 命名空间：`renderBarChart`、`renderPieChart`、`renderDoughnutChart`、`renderLineChart`、`renderRadarChart`、`renderSemiDoughnutChart`。8 色调色板与 `constants.py` 对齐。

### 4.10 台账类型体系（13 种）
`incoming`（进场）、`transfer`（调拨）、`measure_rebar`（措施筋）、`inventory`（剩余）、`waste`（废料）、`model_quantity`（模型量）、`secondary`（二构）、`detailing`（翻样）、`non_budget`（非预算）、`pile_foundation`（主体桩基）、`support_structure`（基坑支护）、`progress`（进度）、`fangyang_requisition`

### 4.11 BOM 树形结构
Buildings → Floors → Areas → Components（6 种类型：column/beam/slab/wall/stair/other）→ RebarDetails。`ImportBatch` 记录导入批次状态机（pending→processing→done/failed→approved/rejected）。

### 4.12 项目分析缓存
`ProjectAnalysis` 表是计算缓存，由 `analysis_service.py::recalc_project_analysis()` 从六大台账聚合填充。`ProjectProfitLoss` 同理，由 `pl_service.py` 维护。

---

## 五、常用命令

### Docker Compose（推荐）

```bash
docker compose up -d                  # 启动全部服务
docker compose logs -f app            # 查看应用日志
docker compose logs -f db             # 查看数据库日志
docker compose down                   # 停止服务
docker compose down -v                # 停止并删除数据卷
docker compose build app && docker compose up -d app   # 代码更新后重建
docker compose exec app bash          # 进入应用容器
docker compose exec db mysql -u rebar -p rebar_mgmt    # 进入数据库
```

### 本地开发

```bash
pip install -r requirements.txt
python run.py                         # 开发模式，debug=True，端口 5000
```

### 数据库迁移

```bash
flask db migrate -m "描述变更内容"
flask db upgrade
```

### 部署到云服务器

```bash
# 服务器上拉取最新代码并重建
ssh root@8.156.91.97 "cd /data01/rebar-mgmt && git pull && docker compose up -d --build"

# 健康检查
curl http://8.156.91.97:5000/health
```

---

## 六、部署架构

- **容器**：`rebar-db`（MySQL 8.0）+ `rebar-app`（Flask + waitress）+ `rebar-autoheal`（自动重启不健康容器）
- **宿主机**：systemd 管理（`rebar-mgmt.service` + `rebar-health-watchdog.timer` 每 30 秒健康检查）
- **健康检查**：`/health` 端点返回 JSON，检查数据库连接 + 目录可写性
- **数据持久化**：`mysql_data` 命名卷 + 挂载 `uploads/`、`exports/`、`status/`、`logs/`

---

## 七、项目原则

1. **渐进式开发**：一个阶段完成并验证后再推进下一阶段
2. **安全第一**：密码 bcrypt 哈希、SQLAlchemy ORM 防注入、CSRF 双层防护、角色权限隔离
3. **运维友好**：配置外置（`.env`）、自动迁移、健康检查 + 自动恢复
4. **数据完整性**：Excel 导入有校验、有回滚、有错误提示
