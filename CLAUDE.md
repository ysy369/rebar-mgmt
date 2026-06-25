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
| **管理员 (admin)** | 全部项目数据、全部功能、系统配置、跨项目对比、用户管理 |
| **普通用户 (user)** | 仅操作被授权项目，数据按项目严格隔离 |

成员角色（`UserProject.role`）：`engineer`（精管工程师）/ `reviewer`（审核员）/ `viewer`（查看员）

---

## 三、侧边栏菜单结构（8 个一级菜单组）

`base.html` 中硬编码，通过 `data-menu-key` + JS `toggleMenu()` 展开/折叠。展开状态持久化到 `localStorage`（键：`expandedMenus_{context}_{projectId}`）。

| # | 菜单组 | menu-key | 类型 | 子菜单项 |
|---|--------|----------|------|----------|
| 1 | **首页** | `no-children` | 直接链接 | → `/home/` |
| 2 | **项目数据看板** | `no-children` | 直接链接（新窗口） | → `/project/dashboard` |
| 3 | **劳务分包管理** | `no-children` | 直接链接（新窗口） | → `/labor/` |
| 4 | **项目管理** | `no-children` | 直接链接 | → `/project/overview`（项目概况列表） |
| 5 | **文件管理** | `file_management` | 可展开 | 文件导入、钢筋模型表、钢筋进场表、调拨钢筋表、废料钢筋表、钢筋剩余表、钢筋二构表、钢筋翻样表、主体桩基表、基坑支护表、非预算收入使用钢筋表 |
| 6 | **审核与分析** | `audit` | 可展开 | 盈亏分析、数据动态管理分析、钢筋采购计划、钢筋对比测算（二级子菜单：盘螺对比/定尺余料对比/余料临界值） |
| 7 | **现场管理** | `site` | 可展开 | 形象进度、钢筋物资领用、巡检管理、钢筋代换、钢筋优化台账 |
| 8 | **系统设置** | `system` | 可展开 | 用户管理 |

菜单高亮规则：
- **一级菜单**（`no-children`）：对比 `request.endpoint`（如 `ep == 'home.index'`）
- **可展开菜单**：通过模板变量 `active_menu` 匹配 `data-menu-key`
- **子菜单**：对比 `request.endpoint` 精确匹配

---

## 四、Blueprint 架构（14 个模块）

| 文件 | Blueprint | url_prefix | 职责 |
|------|-----------|------------|------|
| `app/routes/home.py` | `home_bp` | `/home` | 首页：KPI 看板 + 工作台（16 入口）+ 管理模块 + 图表 |
| `app/routes/project.py` | `project_bp` | `/project` | 项目详情（5 Tab）/ 数据看板 / 文件导入 / 10 种台账表 / 料单 / 成本 / 盈亏 / 附件管理 |
| `app/routes/dashboard.py` | `dashboard_bp` | *(无)* | 深色科技数据看板（`/dashboard`）；被 project.py 导入复用计算函数 |
| `app/routes/labor.py` | `labor_bp` | `/labor` | 劳务分包管理（独立全屏深色页面） |
| `app/routes/audit.py` | `audit_bp` | `/audit` | 盈亏分析 / 数据动态 / 采购计划 / 对比测算（3 子类） |
| `app/routes/site.py` | `site_bp` | `/site` | 形象进度 / 物资领用 / 巡检 / 钢筋代换 / 优化台账 |
| `app/routes/work.py` | `work_bp` | `/work` | 工作管理（3 Tab：责任矩阵/计划管理/标准文件） |
| `app/routes/system.py` | `system_bp` | `/system` | 用户管理（侧边栏「系统设置」入口） |
| `app/routes/admin.py` | `admin_bp` | `/admin` | 甲方单位 CRUD / 承接公司 CRUD / 项目 CRUD / 料单审核 / 跨项目盈亏看板 / 全局重算 / 用户管理 |
| `app/routes/bom.py` | `bom_bp` | `/bom` | 配料单 BOM：看板→导入→汇总→构件明细→审核→导出 |
| `app/routes/ledger.py` | `ledger_bp` | `/ledger` | 6 种核心台账详情页 + 形象进度 CRUD + 结余率分析导出 |
| `app/routes/settlement.py` | `settlement_bp` | `/settlement` | 结算分析 / 结算文件 |
| `app/routes/api.py` | `api_bp` | `/api` | JSON API：级联下拉（按甲方/承接公司查项目） |
| `app/routes/auth.py` | `auth_bp` | `/auth` | 登录（含平台选择 Tab）/ 登出 |

---

## 五、各模块端点详情

### 5.1 首页工作台 (`home_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/home/` | GET | 首页：全局筛选（甲方/承接公司/项目/状态/周期）+ KPI 深色卡片（5 项）+ 白色指标卡（4 项）+ 图表 + 工作台 16 入口 |

工作台分两组，每组 8 个快捷入口：
- **业务入口**：钢筋预算、钢筋翻样、钢筋物资、策划管理、巡检台帐、盈亏分析、结算管理、分包领用
- **综合管理**：策划跟踪、项目交底、图纸答疑、扣费材料、非施料单、材料计划、原材库余、罚通联扣

### 5.2 项目数据看板 (`project_bp` / `dashboard_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/dashboard` | GET | 深色科技全屏看板：三栏布局（选中周期/全期对比/前期），KPI 状态标签，物资指数，12 月趋势图，预警列表，顶部导航菜单 |
| `/project/dashboard` | GET | 复用 `/dashboard` 模板，增加项目筛选下拉 |

顶部导航菜单（仅管理员可见后 4 项）：数据看板 → 钢筋台账 → 方样料单 → 项目管理 → 料单审核 → 盈亏分析 → 用户管理

### 5.3 项目管理 (`project_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/project/overview` | GET | 项目概况列表页（卡片视图） |
| `/project/list` | GET | 在建项目列表（含 BOM 构件数/吨数统计） |
| `/project/<id>/detail?tab=` | GET | 项目详情页 **5 个 Tab**：概览 / 项目成员 / 台账数据 / 结算分析 / 盈亏分析 |
| `/project/<id>/detail/members/add` | POST | 添加项目成员 |
| `/project/<id>/detail/members/<uid>/remove` | POST | 移除项目成员 |
| `/project/<id>/detail/settlement/export` | GET | 导出结算分析 Excel |
| `/project/<id>/attachments` | GET | 模型效果图管理 |
| `/project/<id>/attachments/upload` | POST | 上传附件（仅图片） |
| `/project/<id>/attachments/<id>/delete` | POST | 删除附件 |
| `/project/<id>/attachments/<id>/cover` | POST | 设为封面 |
| `/project/<id>/attachments/<id>/file` | GET | 查看原图 |
| `/project/<id>/cutting-orders` | GET | 料单台账列表 |
| `/project/<id>/cutting-orders/create` | GET/POST | 创建料单 |
| `/project/<id>/cutting-orders/<oid>` | GET | 料单详情 + 明细列表 |
| `/project/<id>/cutting-orders/<oid>/add-item` | POST | 添加料单明细 |
| `/project/<id>/cutting-orders/<oid>/delete-item/<iid>` | POST | 删除明细 |
| `/project/<id>/cutting-orders/<oid>/submit` | POST | 提交审核 |
| `/project/<id>/cutting-orders/<oid>/delete` | POST | 删除料单 |
| `/project/<id>/costs` | GET | 项目成本列表 + 汇总 |
| `/project/<id>/costs/create` | GET/POST | 录入成本（6 类别：人工/材料/设备/运输/管理/其他） |
| `/project/<id>/costs/<cid>/edit` | GET/POST | 编辑成本 |
| `/project/<id>/costs/<cid>/delete` | POST | 删除成本 |
| `/project/<id>/pl-analysis` | GET | 项目盈亏分析（节超收益 + 成本 + 净利润 + 利润率） |
| `/project/<id>/pl-analysis/update-price` | POST | 更新节约定价 |
| `/project/<id>/pl-analysis/update-other-income` | POST | 更新其他收入 |

### 5.4 文件管理 — 10 种台账表 (`project_bp`)

这些路由通过 `_render_sheet()` 通用函数渲染，展示该类型的 `ImportedFile` 导入文件列表（分页、搜索）：

| 路由 | 视图名 | 台账类型 | 中文标签 |
|------|--------|----------|----------|
| `/project/model-sheet` | `model_sheet` | `model_quantity` | 钢筋模型表 |
| `/project/entry-sheet` | `entry_sheet` | `incoming` | 钢筋进场表 |
| `/project/transfer-sheet` | `transfer_sheet` | `transfer` | 调拨钢筋表 |
| `/project/waste-sheet` | `waste_sheet` | `waste` | 废料钢筋表 |
| `/project/remaining-sheet` | `remaining_sheet` | `inventory` | 钢筋剩余表 |
| `/project/secondary-sheet` | `secondary_sheet` | `secondary` | 钢筋二构表 |
| `/project/detailing-sheet` | `detailing_sheet` | `detailing` | 钢筋翻样表 |
| `/project/pile-foundation-sheet` | `pile_foundation_sheet` | `pile_foundation` | 主体桩基表 |
| `/project/support-structure-sheet` | `support_structure_sheet` | `support_structure` | 基坑支护表 |
| `/project/non-budget-sheet` | `non_budget_sheet` | `non_budget` | 非预算收入使用钢筋表 |

此外还有文件导入/下载/删除路由：
| `/project/import?type=` | GET/POST | 上传文件到 `imported_files` 表 |
| `/project/imported-files/<id>/download` | GET | 下载导入源文件 |
| `/project/imported-files/<id>/delete` | POST | 删除导入记录 + 物理文件 |

**文件管理包装路由**（从项目管理进入时透传 `active_menu`）：
`/project/<id>/files/incoming`, `/transfer`, `/measure_rebar`, `/inventory`, `/waste`, `/progress`, `/model_quantity`, `/import`

### 5.5 核心台账详情页 (`ledger_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/ledger/<pid>/incoming` | GET | 进场台账：分页/日期筛选/单位切换（T/kg） |
| `/ledger/<pid>/transfer` | GET | 调拨台账：方向筛选（in/out）、类型（raw/semi） |
| `/ledger/<pid>/measure` | GET | 措施筋台账：预算内/非预算分类 |
| `/ledger/<pid>/inventory` | GET | 盘点表：原材/短料/半成品/合计 |
| `/ledger/<pid>/waste` | GET | 废料台账 |
| `/ledger/<pid>/progress` | GET | 形象进度汇总（按楼栋分组） |
| `/ledger/<pid>/progress/<building>` | GET | 某楼栋进度明细 |
| `/ledger/<pid>/progress/add` | POST | 手动添加进度记录 |
| `/ledger/<pid>/progress/<pid>/edit` | POST | 编辑进度记录 |
| `/ledger/<pid>/progress/<pid>/delete` | POST | 删除进度记录 |
| `/ledger/<pid>/import/<dtype>` | GET/POST | 统一导入入口（incoming/transfer/measure/inventory/waste） |
| `/ledger/<pid>/export-analysis` | GET | 结余率分析 Excel 导出 |

### 5.6 配料单 BOM (`bom_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/bom/dashboard` | GET | BOM 模块首页：项目列表 |
| `/bom/<pid>/import` | GET/POST | 批量导入 Excel → 解析为 Building→Floor→Area→Component→RebarDetail 五级树 |
| `/bom/<pid>/summary` | GET | 数据汇总：树形浏览 + 构件列表 + 按类型/楼层统计图表 |
| `/bom/<pid>/component/<cid>` | GET | 构件钢筋明细 |
| `/bom/<pid>/component/<cid>/status` | POST | 更新构件施工状态 |
| `/bom/<pid>/component/<cid>/edit-weight` | POST | 编辑钢筋重量（JSON API） |
| `/bom/<pid>/batch-status` | POST | 批量更新构件状态 |
| `/bom/<pid>/export` | GET | 导出项目汇总 Excel |
| `/bom/<pid>/batch/<bid>/delete` | POST | 删除导入批次（级联删除数据） |
| `/bom/<pid>/batch/<bid>/download` | GET | 下载批次源文件 |
| `/bom/<pid>/api/tree` | GET | 项目树 JSON API |
| `/bom/<pid>/api/status-summary` | GET | 状态统计 JSON API |
| `/bom/admin/review` | GET | 管理员：全部批次审核列表 |
| `/bom/<pid>/admin/review` | GET | 管理员：某项目批次审核 |
| `/bom/admin/review/<bid>` | POST | 审核操作（approved/rejected） |

### 5.7 审核与分析 (`audit_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/audit/profit-loss` | GET | 盈亏分析 |
| `/audit/data-dynamic` | GET | 数据动态管理分析 |
| `/audit/procurement-plan` | GET | 钢筋采购计划 |
| `/audit/comparison-calc?category=` | GET | 钢筋对比测算（coil=盘螺/fixed=定尺余料/threshold=余料临界值） |

### 5.8 现场管理 (`site_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/site/visual-progress` | GET | 形象进度 |
| `/site/material-issue` | GET | 钢筋物资领用 |
| `/site/inspection` | GET | 巡检管理 |
| `/site/rebar-replacement` | GET | 钢筋代换 |
| `/site/optimization-ledger` | GET | 钢筋优化台账 |

### 5.9 劳务分包 (`labor_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/labor/` | GET | 独立深色全屏大屏：楼栋明细表 + 盈亏罚扣（左右两组）+ 总结算量/报量预警 |

### 5.10 工作管理 (`work_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/work/` | GET | 工作管理（3 Tab：责任矩阵 / 计划管理 / 标准文件） |

### 5.11 结算管理 (`settlement_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/settlement/<pid>/analysis` | GET | 结余率分析 |
| `/settlement/<pid>/documents` | GET | 结算文件管理 |

### 5.12 管理端 (`admin_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/admin/contractors` | GET | 承接公司列表 |
| `/admin/contractors/create` | GET/POST | 创建承接公司 |
| `/admin/contractors/<id>/edit` | GET/POST | 编辑承接公司 |
| `/admin/contractors/<id>/delete` | POST | 删除承接公司 |
| `/admin/client-units` | GET | 甲方单位列表 |
| `/admin/client-units/create` | GET/POST | 创建甲方单位 |
| `/admin/client-units/<id>/edit` | GET/POST | 编辑甲方单位 |
| `/admin/client-units/<id>/delete` | POST | 删除甲方单位 |
| `/admin/projects` | GET | 项目列表（含甲方/承接公司关联） |
| `/admin/projects/create` | GET/POST | 创建项目（含合同/工程地点/服务范围等字段） |
| `/admin/projects/<id>/edit` | GET/POST | 编辑项目 |
| `/admin/projects/<id>/delete` | POST | 删除项目 |
| `/admin/cutting-orders` | GET | 全部料单审核列表（按状态/项目筛选） |
| `/admin/cutting-orders/<oid>` | GET | 审核料单详情 |
| `/admin/cutting-orders/<oid>/review` | POST | 审核操作（reviewed/approved/rejected） |
| `/admin/pl-dashboard` | GET | 跨项目盈亏看板 |
| `/admin/recalc-all` | GET | 重算所有项目分析数据 |
| `/admin/users` | GET | 用户管理列表 |
| `/admin/users/create` | GET/POST | 创建用户 |
| `/admin/users/<id>/edit` | GET/POST | 编辑用户 |
| `/admin/users/<id>/toggle` | POST | 启用/禁用用户 |
| `/admin/users/<id>/delete` | POST | 删除用户 |

### 5.13 系统设置 (`system_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/system/users` | GET | 用户列表（侧边栏「系统设置→用户管理」入口） |
| `/system/users/create` | GET/POST | 创建用户 |
| `/system/users/<id>/edit` | GET/POST | 编辑用户 |
| `/system/users/<id>/toggle` | POST | 启用/禁用 |
| `/system/users/<id>/delete` | POST | 删除用户 |

> **注意**：`system_bp` 和 `admin_bp` 都有用户管理 CRUD，功能几乎相同。`system_bp` 用于侧边栏入口，`admin_bp` 用于深色看板顶部导航入口。

### 5.14 认证 (`auth_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/auth/login` | GET/POST | 登录（支持平台选择：精管/精算/成本管理） |
| `/auth/logout` | GET | 登出 |

### 5.15 JSON API (`api_bp`)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/projects/by-client/<id>` | GET | 按甲方查询项目（级联下拉） |
| `/api/projects/by-contractor/<id>` | GET | 按承接公司查询项目 |
| `/api/clients` | GET | 全部甲方单位 |
| `/api/contractors` | GET | 全部承接公司 |

---

## 六、数据模型（25 张表）

### 6.1 核心业务表

| 表名 | 模型 | 说明 |
|------|------|------|
| `users` | `User` | 用户（bcrypt 密码哈希） |
| `client_units` | `ClientUnit` | 甲方单位 |
| `contractors` | `Contractor` | 承接公司 |
| `projects` | `Project` | 项目（含合同/工程/服务字段） |
| `user_projects` | `UserProject` | 用户-项目授权关联 |

### 6.2 钢筋台账表（`app/models/rebar.py`）

| 表名 | 模型 | 说明 |
|------|------|------|
| `incoming` | `Incoming` | 进场台账（过磅重量/车牌/规格/使用部位） |
| `transfer` | `Transfer` | 调拨台账（原材/半成品，调入/调出） |
| `measure_rebar` | `MeasureRebar` | 措施筋台账（预算内/非预算分类） |
| `inventory` | `Inventory` | 盘点/剩余表（原材/短料/半成品/合计） |
| `waste` | `Waste` | 废料台账（过磅/处理） |
| `model_quantity` | `ModelQuantity` | 模型量/主体结构量（主体+二构） |
| `project_analysis` | `ProjectAnalysis` | 项目分析汇总缓存（①~⑬ 指标） |

### 6.3 BOM 配料单表（`app/models/bom.py`）

| 表名 | 模型 | 说明 |
|------|------|------|
| `buildings` | `Building` | 楼栋 |
| `floors` | `Floor` | 楼层 |
| `areas` | `Area` | 区域 |
| `components` | `Component` | 构件（6 种类型 + 3 种施工状态） |
| `rebar_details` | `RebarDetail` | 钢筋明细（直径/重量/根数/长度） |
| `import_batches` | `ImportBatch` | 导入批次（状态机：pending→processing→done/failed→approved/rejected） |

### 6.4 业务扩展表（`app/models/business.py`）

| 表名 | 模型 | 说明 |
|------|------|------|
| `project_attachments` | `ProjectAttachment` | 项目附件/效果图 |
| `cutting_orders` | `CuttingOrder` | 料单主表（状态机：draft→submitted→reviewed→approved/rejected） |
| `cutting_order_items` | `CuttingOrderItem` | 料单明细 |
| `project_costs` | `ProjectCost` | 项目成本（6 类别：人工/材料/设备/运输/管理/其他） |
| `project_profit_loss` | `ProjectProfitLoss` | 项目盈亏缓存（节超收益+成本→净利润） |

### 6.5 辅助表

| 表名 | 模型 | 说明 |
|------|------|------|
| `imported_files` | `ImportedFile` | 导入文件记录（13 种 ledger_type） |
| `building_progress` | `BuildingProgress` | 形象进度（楼栋/楼层/构件进度） |
| `import_logs` | `ImportLog` | 导入日志 |
| `operation_logs` | `OperationLog` | 操作审计日志 |

---

## 七、台账类型完整体系（13 种）

定义在 `project.py:LEDGER_TYPE_LABELS` 和 `imported_file.py` 枚举中：

| 类型键 | 中文标签 | 数据表 | 侧边栏展示 |
|--------|----------|--------|------------|
| `model_quantity` | 钢筋模型表 | `model_quantity` | ✅ |
| `incoming` | 钢筋进场表 | `incoming` | ✅ |
| `transfer` | 调拨钢筋表 | `transfer` | ✅ |
| `waste` | 废料钢筋表 | `waste` | ✅ |
| `inventory` | 钢筋剩余表 | `inventory` | ✅ |
| `secondary` | 钢筋二构表 | （model_quantity.secondary_weight） | ✅ |
| `detailing` | 钢筋翻样表 | — | ✅ |
| `non_budget` | 非预算收入使用钢筋表 | — | ✅ |
| `pile_foundation` | 主体桩基表 | — | ✅ |
| `support_structure` | 基坑支护表 | — | ✅ |
| `measure_rebar` | 措施筋台账 | `measure_rebar` | ❌（ledger 独立页） |
| `fangyang_requisition` | 方样料单 | — | ❌ |
| `progress` | 形象进度 | `building_progress` | ❌（ledger 独立页） |

`SHEET_LEDGER_MAP`（10 项）将视图名映射到台账类型，用于侧边栏文件管理子菜单。

---

## 八、关键架构模式

### 8.1 启动时自动迁移 `_auto_migrate()`
- 在 `create_app()` 中调用，**独立于 Flask-Migrate**
- 通过 `information_schema` 检查列是否存在，幂等添加缺失列
- 自动创建 `imported_files` 表并扩展其 `ledger_type` 枚举
- 自动将 `projects.status` 从 enum 转为 varchar(20)
- **新增字段只需在 `_auto_migrate()` 中添加一条迁移记录即可**——无需手动 SQL

### 8.2 CSRF 防护（双层机制）
- **服务端**：`before_request` 拦截 POST/PUT/DELETE/PATCH，验证 `session["_csrf_token"]`，登录端点跳过
- **客户端**：`app.js` 自动从 `<meta name="csrf-token">` 读取 token，注入所有 POST 表单隐藏域
- **模板中直接用 `{{ csrf_field|safe }}` 或什么都不写**——JS 会自动注入

### 8.3 模板上下文自动注入
`context_processor` (`inject_globals`) 向所有模板注入：
- `csrf_token`、`csrf_field`（已渲染的隐藏 input）
- `current_project` — 当路由以 `project.`/`ledger.`/`bom.` 开头时自动从 `view_args` 解析
- `platform_type` — 当前登录时选择的平台类型（`jinguan`/`jingsuan`/`cost`），从 session 读取
- `period_options` — 最近 24 个月的 YYYY-MM 下拉选项
- `APP_NAME`、`APP_VERSION`

### 8.4 模板全局变量（来自 `app/services/constants.py`）
15 个 `*_MAP` 字典注入所有模板：`PROJECT_STATUS_MAP`、`CUTTING_ORDER_STATUS_MAP`、`COMPONENT_TYPE_MAP`、`TRANSFER_DIRECTION_MAP` 等。配合 `status_badge()` 宏使用。

### 8.5 模板过滤器
`|format_ton(1)` → 保留 1 位小数的吨数（默认 3 位）、`|format_kg`、`|format_money`、`|format_percent`

### 8.6 双主题模式
- **亮色标准**：继承 `base.html`，侧边栏 + 顶栏布局，用于管理后台页面
- **深色科技**：**独立 HTML 文档**，不继承 `base.html`，直接加载 CDN 资源，用于大屏看板（`dashboard/index.html`、`labor/fullscreen.html`）。配色：`#0a1628` 背景 + `#00d4ff` 青色 + `#ff7a00` 橙色

### 8.7 宏系统（`_macros.html`）
15 个可复用宏：`stat_card`、`status_badge`、`data_table`、`empty_state`、`render_pagination`、`chart_card`、`confirm_delete_form`、`render_breadcrumb`、`render_sidebar_menus`、`page_header`、`filter_reset_button`、`card_table`、`period_select`、`unit_select`、`stat_card_small`

### 8.8 图表封装（`charts.js`）
`window.RebarCharts` 命名空间：`renderBarChart`、`renderPieChart`、`renderDoughnutChart`、`renderLineChart`、`renderRadarChart`、`renderSemiDoughnutChart`。8 色调色板与 `constants.py` 对齐。

### 8.9 BOM 树形结构
Buildings → Floors → Areas → Components（6 种类型：column/beam/slab/wall/stair/other，3 种状态：not_started/in_progress/poured）→ RebarDetails。`ImportBatch` 记录导入批次状态机（pending→processing→done/failed→approved/rejected）。

### 8.10 项目分析缓存
`ProjectAnalysis` 表是计算缓存，由 `analysis_service.py::recalc_project_analysis()` 从原始台账聚合填充。`ProjectProfitLoss` 同理，由 `pl_service.py` 维护。

### 8.11 权限装饰器

两个关键装饰器，定义在 `app/services/auth_service.py`：

| 装饰器 | 用途 | 失败行为 |
|--------|------|---------|
| `@admin_required` | 仅管理员可访问 | 403 |
| `@project_access_required` | 检查用户是否有该项目的 `UserProject` 关联；admin 自动通过 | 403 |

使用方式：
```python
@project_bp.route("/<int:project_id>/detail")
@login_required
@project_access_required    # 放在 @login_required 下面
def project_detail(project_id):
    ...
```

`project_access_required` 从 `kwargs` 中取 `project_id` 或 `id`，调用 `can_access_project()` 查询 `UserProject` 关联表。

### 8.12 面包屑 `_bc()` 约定

每个蓝图文件顶部都有一个**同名的本地函数** `_bc(*items)`，用于构建面包屑导航：

```python
def _bc(*items):
    base = [{"name": "钢筋管理平台", "url": url_for("home.index")}]
    base.extend(items)
    return base
```

所有 `render_template` 调用都传入 `breadcrumbs=_bc({"name": "xxx"}, ...)`，由 `base.html` 中的 `render_breadcrumb` 宏统一渲染。

### 8.13 菜单高亮透传（`active_menu` / `active_submenu`）

当 `project.py` 的路由包装了 `ledger.py` 或 `bom.py` 的视图时，通过**可选参数透传**保持侧边栏菜单正确高亮：

```python
# ledger.py 的函数签名接受可选参数
def incoming_list(project_id, active_menu="file_management", active_submenu="incoming"):
    ...

# project.py 调用时透传确保菜单高亮
from app.routes.ledger import incoming_list
return incoming_list(project_id, active_menu="file_management", active_submenu="incoming")
```

这样同一个台账页面从"项目管理"和"文件管理"两个不同入口进入时，侧边栏分别高亮对应的菜单项。

### 8.14 `_render_sheet()` 通用台账表渲染

`project.py` 中的 `_render_sheet(view_name)` 函数是 10 个台账表路由的统一实现：

```python
def _render_sheet(view_name):
    ledger_type = SHEET_LEDGER_MAP.get(view_name)     # 映射到台账类型
    page_title = LEDGER_TYPE_LABELS.get(ledger_type)   # 中文标签
    search = request.args.get("search", "").strip()
    query = _get_imported_files_query(ledger_type, search)  # 查 imported_files 表
    pagination = paginate(query, per_page=20)
    return render_template("project/sheet_base.html", ...)
```

所有 10 个台账表页面共用同一个模板 `project/sheet_base.html`，展示该类型的导入文件列表。

### 8.15 料单（CuttingOrder）状态机

定义在 `app/services/cutting_order_service.py` 的 `TRANSITIONS` 字典中：

```
draft ─→ submitted ─→ reviewed ─→ approved  （终态）
  ↑                      ↘ rejected ─→ draft （驳回后可修改重提）
  └───────────────────────────────────────────（draft/rejected 状态可编辑）
```

审核流程记录 `submitted_by`、`reviewed_by`、`submitted_at`、`reviewed_at` 等审计字段。

### 8.16 台账导入 → 分析重算自动触发链

导入流程的完整链路：
1. `ledger.import_data()` 接收 Excel → 调用 `ledger_import.py` 中对应解析函数
2. 解析函数写入对应数据表（Incoming / Transfer / MeasureRebar / Inventory / Waste）
3. **自动调用** `analysis_service.recalc_project_analysis(project_id)` 更新 `ProjectAnalysis` 缓存
4. 同时调用 `pl_service.recompute_project_pl(project_id)` 更新 `ProjectProfitLoss` 缓存

**新增台账数据后，分析看板和盈亏数据自动刷新，无需手动触发。**

### 8.17 模型导入约定

所有模型在 `app/models/__init__.py` 中按依赖顺序统一导出。始终从 `app.models` 导入模型：

```python
from app.models import User, Project, UserProject  # ✅ 正确
from app.models.user import User                     # ❌ 避免（可能触发循环导入）
```

新增模型文件后需要在 `__init__.py` 中添加对应 import。

### 8.18 配置加载机制

`config.py` 定义了两个配置类，通过环境变量 `FLASK_ENV` 选择：

| 类 | FLASK_ENV | DEBUG | DATABASE_URL 默认值 |
|----|-----------|-------|-------------------|
| `DevelopmentConfig` | `development` | True | `127.0.0.1:3306` |
| `ProductionConfig` | `production` | False | `localhost:3306` |

**关键**：`DATABASE_URL` 优先从环境变量读取。Docker Compose 中通过 `environment` 注入。

`SECRET_KEY` 默认用 `os.urandom(32).hex()`（每次重启随机生成），**生产环境必须在 `.env` 或 docker-compose.yml 中固定**，否则每次重启所有用户 session 失效。

### 8.19 双用户管理系统

项目中存在两套用户管理路由，功能几乎一致：

| 入口 | Blueprint | 路由前缀 | 使用场景 |
|------|-----------|----------|----------|
| 侧边栏「系统设置→用户管理」 | `system_bp` | `/system/users` | 日常管理 |
| 深色看板顶部导航「用户管理」 | `admin_bp` | `/admin/users` | 管理员快捷入口 |

两个入口都受 `@admin_required` 保护，共享相同的 `User` 模型和模板。

---

## 九、常用命令

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
# 服务器已初始化 git 并关联 GitHub（Deploy Key 只读），直接 git pull 部署
ssh root@8.156.91.97 "cd /data01/rebar-mgmt && git pull && docker compose up -d --build app"

# 健康检查
curl http://8.156.91.97:5000/health
```

---

## 十、部署架构

- **容器**：`rebar-db`（MySQL 8.0）+ `rebar-app`（Flask + waitress）+ `rebar-autoheal`（自动重启不健康容器）
- **宿主机**：systemd 管理（`rebar-mgmt.service` + `rebar-health-watchdog.timer` 每 30 秒健康检查）
- **健康检查**：`/health` 端点返回 JSON，检查数据库连接 + 目录可写性
- **数据持久化**：`mysql_data` 命名卷 + 挂载 `uploads/`、`exports/`、`status/`、`logs/`
- **代码更新**：服务器已初始化 git 并配置 GitHub Deploy Key（只读），`git pull` + `docker compose up -d --build app` 即可更新
- **⚠️ SECRET_KEY**：生产环境必须在 `.env` 或 `docker-compose.yml` 中固定，否则每次重建 session 全部失效

---

## 十一、项目原则

1. **渐进式开发**：一个阶段完成并验证后再推进下一阶段
2. **安全第一**：密码 bcrypt 哈希、SQLAlchemy ORM 防注入、CSRF 双层防护、角色权限隔离
3. **运维友好**：配置外置（`.env`）、自动迁移、健康检查 + 自动恢复
4. **数据完整性**：Excel 导入有校验、有回滚、有错误提示
