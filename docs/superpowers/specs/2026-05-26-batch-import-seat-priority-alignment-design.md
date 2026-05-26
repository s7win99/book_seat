# 批量导入用户、座位优先展示、布局对齐优化 — 设计文档

日期：2026-05-26

## 概述

三项功能改进：
1. 管理员批量导入用户（CSV 格式）
2. 座位概览页优先展示自己的固定座位或已签到座位
3. 修复多页面因右侧元素宽度不一导致的用户名对齐问题

---

## 一、批量导入用户

### 功能描述

管理员在"用户管理"标签页点击"批量导入"按钮，选择 CSV 文件上传，系统逐行创建用户并返回导入结果。

### CSV 格式

```csv
username,name,password
zhangsan,张三,123456
lisi,李四,123456
wangwu,王五,mypass123
```

- 第一行为表头，必须为 `username,name,password`
- 三个字段均为必填
- 用户名重复的行自动跳过
- 编码：UTF-8（兼容带 BOM 的 UTF-8，Excel 导出常见）

### 后端

**新接口：** `POST /api/admin/users/import`

- 接收 `multipart/form-data`，字段名为 `file`
- 使用 Python `csv` 模块解析（无需额外依赖）
- 逐行处理：
  - 跳过表头
  - 校验三个字段非空
  - 检查用户名是否已存在，存在则跳过
  - 创建用户（密码使用 bcrypt 哈希）
- 返回 JSON 结果：
  ```json
  {
    "total": 10,
    "success": 8,
    "skipped": 2,
    "skipped_users": ["zhangsan", "lisi"],
    "errors": []
  }
  ```

**涉及文件：** `backend/routers/admin.py`（新增路由函数）

### 前端

- 在用户管理标签页的"+ 添加用户"按钮旁边新增"批量导入"按钮（蓝色样式）
- 使用隐藏的 `<input type="file" accept=".csv">` 触发文件选择
- 选择文件后自动上传，上传期间按钮显示"导入中..."
- 上传完成后弹出结果摘要：
  - 成功导入 X 人
  - 跳过 Y 人（列出跳过的用户名）
  - 错误信息（如有格式问题）

**涉及文件：** `frontend/src/views/Admin.vue`

---

## 二、座位概览页优先展示自己的座位

### 功能描述

在 `SeatOverview.vue` 的筛选按钮下方、座位列表上方，新增一个"我的座位"分区，始终置顶显示。

### 显示逻辑

| 用户状态 | 显示内容 | 样式 |
|---------|---------|------|
| 已签到 | 当前签到座位名 + 已用时间 | 绿色左边框 |
| 有固定座位（未签到） | 固定座位名 + 类型 | 蓝色左边框 |
| 两者都有 | 两个卡片垂直排列 | 各自样式 |
| 都没有 | 不显示此分区 | — |

### 前端改动

**涉及文件：** `frontend/src/views/SeatOverview.vue`

- 在 `filteredSeats` 列表上方新增条件渲染区域
- 需要额外数据：当前用户的固定座位信息
  - 方案：从已有的 `/api/seats` 返回数据中过滤（`seat.assigned_user_id === auth.user.id && seat.seat_type === 'fixed'`），无需新增接口
- 已签到信息已有（`status` 变量中包含 `seat_name`、`elapsed_minutes`）
- 新增 CSS 样式：`.my-seat-section`、`.my-seat-card`（绿/蓝边框卡片）

---

## 三、布局对齐修复

### 问题分析

| 页面 | 问题描述 |
|------|---------|
| NavBar.vue | 用户名长度不固定，右侧按钮位置随用户名变化 |
| Admin.vue 用户列表 | `row-actions` 含 select + 多按钮，宽度不固定 |
| Admin.vue 座位列表 | 5 个按钮，窄屏时可能挤压左侧名称 |
| SeatOverview.vue | `seat-status` 中占用者名称长度不一（影响较小） |

Leaderboard.vue 和 MyAttendance.vue 已正确使用 `flex: 1`，无问题。

### 修复方案（统一模式）

所有列表行统一采用：
- 左侧名称区：`flex: 1; min-width: 0; overflow: hidden`
- 名称文本：`text-overflow: ellipsis; white-space: nowrap`
- 右侧操作区：`flex-shrink: 0`（不被压缩）

具体改动：

**NavBar.vue**
- `.nav-user span` 添加 `max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap`

**Admin.vue**
- `.row-info` 添加 `min-width: 0; overflow: hidden`
- `.row-info strong` 添加 `overflow: hidden; text-overflow: ellipsis; white-space: nowrap`
- `.row-actions` 添加 `flex-shrink: 0`

**SeatOverview.vue**
- `.seat-status` 添加 `flex-shrink: 0; max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap`

---

## 涉及文件汇总

| 文件 | 改动内容 |
|------|---------|
| `backend/routers/admin.py` | 新增批量导入接口 |
| `frontend/src/views/Admin.vue` | 批量导入按钮 + 对齐修复 |
| `frontend/src/views/SeatOverview.vue` | 我的座位置顶分区 + 对齐修复 |
| `frontend/src/components/NavBar.vue` | 用户名对齐修复 |
