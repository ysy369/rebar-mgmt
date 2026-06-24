# API 接口规范

> 版本：v1.0 | 日期：2026-06-21 | 状态：占位（待第二阶段后补充完整）

---

## 1. 概述

本项目采用传统服务端渲染（SSR）模式，大部分交互通过 HTML 表单提交完成，部分交互（图表数据加载、Excel 上传预览）使用 JSON API。

### 基础信息
- **Base URL**：`http://<host>:5000`
- **Content-Type**：`application/json`（JSON API）/ `multipart/form-data`（文件上传）
- **认证方式**：Session Cookie（Flask-Login）

## 2. 认证模块 API

> 待第二阶段实现时补充详细定义

| 路由 | 方法 | 说明 |
|------|------|------|
| `/auth/login` | GET | 登录页面 |
| `/auth/login` | POST | 提交登录 |
| `/auth/logout` | GET | 退出登录 |
| `/auth/change-password` | POST | 修改密码 |

## 3. 管理端 API

> 待第三阶段实现时补充详细定义

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/` | GET | 管理端首页 Dashboard |
| `/admin/users/` | GET/POST | 用户管理 |
| `/admin/projects/` | GET/POST | 项目管理 |
| `/admin/client-units/` | GET/POST | 甲方单位管理 |
| `/admin/import/` | GET/POST | 数据导入 |

## 4. 项目端 API

> 待第三阶段实现时补充详细定义

| 路由 | 方法 | 说明 |
|------|------|------|
| `/project/` | GET | 项目端首页 |
| `/project/<id>/` | GET | 项目详情 |
| `/project/<id>/import/` | GET/POST | 项目数据导入 |
| `/project/<id>/report/` | GET | 项目报表 |

## 5. JSON API（图表数据）

> 待第四阶段实现时补充详细定义

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/project/<id>/trend` | GET | 项目结余率趋势数据 |
| `/api/project/<id>/comparison` | GET | 项目分项对比数据 |
| `/api/admin/cross-project` | GET | 跨项目对比数据 |

## 6. 导出 API

> 待第五阶段实现时补充详细定义

| 路由 | 方法 | 说明 |
|------|------|------|
| `/project/<id>/export` | GET | 导出单个项目汇总表 |
| `/admin/export/all` | GET | 导出全局汇总表 |

## 7. 通用响应格式

### 成功响应
```json
{
  "success": true,
  "data": {},
  "message": "操作成功"
}
```

### 错误响应
```json
{
  "success": false,
  "message": "错误描述",
  "errors": {
    "field_name": ["字段级错误信息"]
  }
}
```

---

> 📝 本文件为占位文档，具体接口定义将在各模块实现时逐步补充完整。
