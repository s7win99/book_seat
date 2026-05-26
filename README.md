# 实验室座位考勤系统

基于 QR 码扫描的实验室座位签到与出勤管理系统。

## 功能

- **座位签到/签退** — 扫描座位二维码完成签到，支持座位切换、冷静期防抖
- **座位管理** — 固定座位（绑定用户）和共享座位两种类型
- **出勤统计** — 每日有效出勤 ≥ 180 分钟，周末特殊规则，月度日历视图
- **排行榜** — 按出勤率排名（本周/本月）
- **管理后台** — 用户/座位/出勤管理，批量导入用户，QR 码批量导出

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python, FastAPI, SQLAlchemy, SQLite |
| 前端 | Vue 3, Vite, Pinia, Vue Router |
| 认证 | JWT (24h 过期) |
| 定时任务 | APScheduler (午夜自动签退 + 出勤计算) |

## 快速启动

### 环境要求

- Python 3.10+
- Node.js 18+

### 安装

```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
cd ../frontend
npm install
```

### 启动

**方式一：一键启动（Windows）**

```bash
start.bat
```

**方式二：分别启动**

```bash
# 终端 1 — 后端
cd backend
python -m uvicorn main:app --reload --port 8000

# 终端 2 — 前端
cd frontend
npm run dev
```

前端：http://localhost:5173
后端 API：http://localhost:8000

### 默认管理员

- 用户名：`admin`
- 密码：`admin123`

## 项目结构

```
backend/
  main.py            # 应用入口
  models.py          # 数据模型 (User, Seat, CheckInSession, AttendanceRecord)
  schemas.py         # Pydantic 模式
  auth.py            # JWT 认证
  config.py          # 配置常量
  routers/           # API 路由 (auth, admin, checkin, seats, attendance)
  services/          # 业务逻辑 (签到, 出勤计算, 定时任务)
frontend/
  src/
    views/           # 页面 (Login, SeatOverview, CheckIn, MyAttendance, Leaderboard, Admin)
    components/      # 组件 (NavBar)
    stores/          # Pinia 状态管理
    api/             # Axios 实例
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| GET | `/api/seats` | 座位列表 |
| POST | `/api/checkin` | 签到 |
| POST | `/api/checkout` | 签退 |
| GET | `/api/checkin/status` | 签到状态 |
| GET | `/api/attendance/my` | 我的出勤 |
| GET | `/api/attendance/leaderboard` | 排行榜 |
| POST | `/api/admin/users/import` | 批量导入用户 |
| GET | `/api/admin/seats/qrcode-batch` | 批量导出 QR 码 |

## 服务器部署

### 一键部署（Linux）

```bash
# 下载部署脚本
wget https://raw.githubusercontent.com/s7win99/book_seat/master/deploy.sh

# 执行部署
sudo bash deploy.sh
```

脚本自动完成：安装依赖 → 克隆代码 → 构建前端 → 配置 systemd 服务 → 配置 Nginx

部署完成后访问 `http://服务器IP`，默认管理员：`admin` / `admin123`

### 常用运维命令

```bash
# 查看后端状态
sudo systemctl status lab-attendance

# 查看实时日志
sudo journalctl -u lab-attendance -f

# 重启后端
sudo systemctl restart lab-attendance

# 更新代码
cd /opt/book_seat && sudo git pull && sudo bash deploy.sh
```

## 签到规则

- 每人同时只能签到一个座位
- 固定座位仅限绑定用户使用
- 有固定座位的用户不能使用共享座位
- 切换座位需等待 1 分钟冷静期
- 每日 00:00 自动签退（不计入有效时长）
- 有效出勤：每日 ≥ 180 分钟
