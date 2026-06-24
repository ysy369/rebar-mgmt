# CLAUDE.md — 钢筋精细化管理平台

> AI 助手指引文件。每次对话开始时，Claude 将参考此文件了解项目背景与规范。

---

## 一、项目概述

| 项目 | 说明 |
|------|------|
| **项目名称** | 钢筋精细化管理平台 (Rebar Fine Management Platform) |
| **架构** | B/S 架构（浏览器/服务器），网络版多客户端 |
| **部署** | Windows 云服务器 |
| **后端** | Python 3 + Flask |
| **数据库** | MySQL 8.0+ |
| **前端** | Bootstrap 5 + Chart.js（CDN 引入，无构建工具） |
| **Excel** | openpyxl + pandas（解析与导出） |

## 二、用户角色

| 角色 | 权限 |
|------|------|
| **管理员 (admin)** | 全部项目数据、导入、系统配置、跨项目对比 |
| **普通用户 (user)** | 仅操作被授权的项目，数据按项目严格隔离 |

## 三、目录结构

```
rebar-mgmt/
├── CLAUDE.md                    # ← 本文件
├── README.md                    # 项目说明
├── requirements.txt             # Python 依赖清单
├── config.py                    # 应用配置（数据库连接等）
├── run.py                       # 启动入口
│
├── docs/                        # 📚 项目规范文档
│   ├── 01-需求规格说明书.md
│   ├── 02-技术选型与架构设计.md
│   ├── 03-UI设计规范.md
│   ├── 04-数据库设计.md
│   ├── 05-API接口规范.md
│   └── 06-开发执行计划.md
│
├── dev-log/                     # 📝 每日开发日志
│   └── YYYY-MM-DD.md
│
├── app/                         # 应用主代码
│   ├── __init__.py              # Flask 工厂函数 create_app()
│   ├── models/                  # SQLAlchemy 数据模型
│   ├── routes/                  # Blueprint 路由
│   ├── services/                # 业务逻辑层
│   ├── templates/               # Jinja2 模板
│   └── static/                  # CSS / JS / 图片
│
├── uploads/                     # Excel 上传临时目录
├── exports/                     # Excel 导出临时目录
├── migrations/                  # 数据库迁移脚本
└── tests/                       # 测试用例
```

## 四、开发规范

### 4.1 Python 代码规范
- 遵循 PEP 8 风格
- 使用 Flask 工厂模式（`create_app()`）
- 业务逻辑放在 `app/services/`，路由中只做参数接收和返回
- 数据库操作使用 SQLAlchemy ORM，避免原生 SQL
- 所有用户输入必须校验和转义

### 4.2 前端规范
- 使用 Bootstrap 5 组件，不引入额外 CSS 框架
- 图表使用 Chart.js（CDN 加载）
- 主色调：深蓝 `#1A3C6E`，强调色：亮橙 `#FF7A00`
- 背景色：`#F5F7FA`
- 左侧导航 220px 固定宽度 + 右侧自适应内容区
- 中文字体：Microsoft YaHei

### 4.3 模板规范
- 所有页面继承 `base.html`
- `base.html` 包含：侧边栏、顶部栏、内容区、公共 JS
- 按角色存放在 `templates/admin/` 和 `templates/project/`
- 登录等公共页面放在 `templates/auth/`

### 4.4 数据库规范
- 所有表使用 InnoDB 引擎，UTF-8 字符集
- 主键统一使用自增整数 `id`
- 时间字段使用 `DateTime` 类型，默认 `CURRENT_TIMESTAMP`
- 外键关系用 SQLAlchemy `relationship` 定义
- 数据库迁移使用 Flask-Migrate（Alembic）

## 五、常用命令

### Docker Compose（推荐，无需安装 Python/MySQL）

```bash
# 启动全部服务（首次启动自动构建镜像 + 初始化数据库）
docker compose up -d

# 查看日志
docker compose logs -f app
docker compose logs -f db

# 停止服务
docker compose down

# 停止并删除数据（重新开始）
docker compose down -v

# 重建应用镜像（代码更新后）
docker compose build app
docker compose up -d app

# 进入应用容器调试
docker compose exec app bash

# 进入数据库
docker compose exec db mysql -u rebar -p rebar_mgmt
```

### 本地开发（需 Python 环境）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python run.py

# 数据库迁移（首次）
flask db init
flask db migrate -m "init"
flask db upgrade

# 数据库迁移（后续变更）
flask db migrate -m "描述变更内容"
flask db upgrade
```

## 六、每日开发日志规范

每天开发结束后，在 `dev-log/` 下创建 `YYYY-MM-DD.md`，内容模板：

```markdown
# 开发日志 — YYYY-MM-DD

## 今日完成
- [ ] 事项描述

## 遇到的问题
- 问题描述 & 解决方案

## 明日计划
- [ ] 计划事项

## 备注
其他需要记录的内容
```

## 七、文档索引

| 文档 | 路径 | 用途 |
|------|------|------|
| 需求规格 | [docs/01-需求规格说明书.md](docs/01-需求规格说明书.md) | 完整功能需求 |
| 技术架构 | [docs/02-技术选型与架构设计.md](docs/02-技术选型与架构设计.md) | 技术方案与架构 |
| UI 规范 | [docs/03-UI设计规范.md](docs/03-UI设计规范.md) | 配色/布局/组件 |
| 数据库 | [docs/04-数据库设计.md](docs/04-数据库设计.md) | 表结构与关系 |
| API 规范 | [docs/05-API接口规范.md](docs/05-API接口规范.md) | 接口定义 |
| 执行计划 | [docs/06-开发执行计划.md](docs/06-开发执行计划.md) | 阶段计划与进度 |
| 操作手册 | [docs/07-操作手册.md](docs/07-操作手册.md) | 用户操作说明 |
| 健康与恢复 | [docs/09-健康检查与自动恢复.md](docs/09-健康检查与自动恢复.md) | /health、Docker 与宿主机自动恢复 |
| 每日日志 | [dev-log/](dev-log/) | 每天开发记录 |

## 八、项目原则

1. **渐进式开发**：一个阶段完成并验证后再推进下一阶段，不贪多求快
2. **安全第一**：密码哈希存储、SQL 注入防护、权限严格隔离
3. **运维友好**：配置外置、日志清晰、部署文档完善
4. **数据完整性**：Excel 导入有校验、有回滚、有错误提示
