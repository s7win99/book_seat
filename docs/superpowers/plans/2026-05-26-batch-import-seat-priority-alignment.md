# 批量导入用户、座位优先展示、布局对齐优化 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 CSV 批量导入用户、座位置顶展示自己的座位、修复多页面布局对齐问题

**Architecture:** 后端在 admin router 新增一个 CSV 导入接口；前端在 Admin.vue 添加导入按钮和结果弹窗、SeatOverview.vue 添加"我的座位"分区、多页面 CSS 统一对齐模式

**Tech Stack:** FastAPI, Python csv module, Vue 3 Composition API, CSS flexbox

---

### Task 1: 后端 — 批量导入用户接口

**Files:**
- Modify: `backend/routers/admin.py:1-10` (新增 import 和路由)
- Modify: `backend/schemas.py` (新增 ImportResult schema)

- [ ] **Step 1: 在 schemas.py 新增导入结果 schema**

在 `backend/schemas.py` 末尾追加：

```python
class ImportResult(BaseModel):
    total: int
    success: int
    skipped: int
    skipped_users: list[str]
    errors: list[str]
```

- [ ] **Step 2: 在 admin.py 新增批量导入接口**

在 `backend/routers/admin.py` 的 import 区域追加 `csv` 和 `UploadFile`：

```python
import csv
from fastapi import UploadFile, File
```

然后在 `reset_password` 函数之后（第 70 行后）插入新路由：

```python
@router.post("/users/import", response_model=ImportResult)
def import_users(file: UploadFile = File(...), admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    content = file.file.read()
    # Handle UTF-8 BOM
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())

    if not reader.fieldnames or set(reader.fieldnames) != {"username", "name", "password"}:
        raise HTTPException(status_code=400, detail="CSV 表头必须为: username,name,password")

    total = 0
    success = 0
    skipped = []
    errors = []

    for i, row in enumerate(reader, start=2):
        total += 1
        username = row.get("username", "").strip()
        name = row.get("name", "").strip()
        password = row.get("password", "").strip()

        if not username or not name or not password:
            errors.append(f"第 {i} 行：字段不能为空")
            continue

        if db.query(User).filter(User.username == username).first():
            skipped.append(username)
            continue

        user = User(
            username=username,
            name=name,
            password_hash=hash_password(password),
            role="user",
        )
        db.add(user)
        success += 1

    db.commit()
    return ImportResult(
        total=total,
        success=success,
        skipped=len(skipped),
        skipped_users=skipped,
        errors=errors,
    )
```

同时在文件顶部的 import 中追加 `ImportResult`：

```python
from schemas import UserCreate, UserUpdate, UserOut, SeatCreate, SeatUpdate, SeatOut, AttendanceRecordOut, ImportResult
```

- [ ] **Step 3: 启动后端验证接口可用**

```bash
cd backend && python -m uvicorn main:app --reload --port 8000
```

在另一个终端测试（或用 curl）：

```bash
# 先创建一个测试 CSV
echo 'username,name,password' > /tmp/test_import.csv
echo 'testuser1,测试用户1,123456' >> /tmp/test_import.csv
echo 'testuser2,测试用户2,abcdef' >> /tmp/test_import.csv

# 获取 admin token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 测试导入
curl -X POST http://localhost:8000/api/admin/users/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_import.csv"
```

Expected: `{"total":2,"success":2,"skipped":0,"skipped_users":[],"errors":[]}`

- [ ] **Step 4: 测试重复用户名跳过**

再次导入同一个文件：

```bash
curl -X POST http://localhost:8000/api/admin/users/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_import.csv"
```

Expected: `{"total":2,"success":0,"skipped":2,"skipped_users":["testuser1","testuser2"],"errors":[]}`

- [ ] **Step 5: Commit**

```bash
git add backend/routers/admin.py backend/schemas.py
git commit -m "feat: add batch user import via CSV"
```

---

### Task 2: 前端 — 批量导入用户界面

**Files:**
- Modify: `frontend/src/views/Admin.vue` (添加导入按钮、上传逻辑、结果弹窗)

- [ ] **Step 1: 在用户管理标签页添加批量导入按钮**

在 Admin.vue 的 `<template>` 中，找到用户管理的 `btn-add` 按钮（第 13 行）：

```html
<button class="btn-add" @click="showUserForm = true">+ 添加用户</button>
```

替换为：

```html
<div class="user-actions">
  <button class="btn-add" @click="showUserForm = true">+ 添加用户</button>
  <button class="btn-batch" @click="$refs.importInput.click()" :disabled="importing">
    {{ importing ? '导入中...' : '批量导入' }}
  </button>
  <input ref="importInput" type="file" accept=".csv" style="display:none" @change="handleImport" />
</div>
```

- [ ] **Step 2: 添加导入结果弹窗**

在 `</template>` 前（NavBar 的 modal 之后），追加导入结果弹窗：

```html
<!-- Import Result Modal -->
<div v-if="importResult" class="modal-overlay" @click.self="importResult = null">
  <div class="modal">
    <h3>导入结果</h3>
    <p>总计：{{ importResult.total }} 人</p>
    <p class="success">成功导入：{{ importResult.success }} 人</p>
    <p v-if="importResult.skipped > 0" class="skipped">
      跳过（用户名已存在）：{{ importResult.skipped }} 人
      <span v-if="importResult.skipped_users.length"> — {{ importResult.skipped_users.join('、') }}</span>
    </p>
    <p v-if="importResult.errors.length > 0" class="error">
      {{ importResult.errors.join('；') }}
    </p>
    <div class="modal-actions">
      <button @click="importResult = null">确定</button>
    </div>
  </div>
</div>
```

- [ ] **Step 3: 添加导入相关的 script 逻辑**

在 `<script setup>` 中的 `const attendance = ref([])` 之后追加：

```javascript
const importing = ref(false)
const importResult = ref(null)
```

在函数区域（`cancelCheckin` 函数之后）追加：

```javascript
async function handleImport(event) {
  const file = event.target.files[0]
  if (!file) return
  importing.value = true
  importResult.value = null
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await api.post('/api/admin/users/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    importResult.value = res.data
    await loadUsers()
  } catch (e) {
    alert(e.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
    event.target.value = ''
  }
}
```

- [ ] **Step 4: 添加 user-actions 和弹窗 CSS 样式**

在 `<style scoped>` 中追加：

```css
.user-actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.user-actions .btn-add {
  flex: 1;
  margin-bottom: 0;
}
.skipped {
  color: #e65100;
  font-size: 0.85rem;
  margin: 0;
}
```

- [ ] **Step 5: 启动前端验证**

```bash
cd frontend && npm run dev
```

在浏览器中打开管理页面 → 用户管理 → 点击"批量导入" → 选择一个 CSV 文件 → 确认弹窗显示导入结果。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/Admin.vue
git commit -m "feat: add batch user import UI in admin panel"
```

---

### Task 3: 座位概览页 — 优先展示自己的座位

**Files:**
- Modify: `frontend/src/views/SeatOverview.vue` (添加"我的座位"分区 + 样式)
- Modify: `frontend/src/stores/auth.js` (确认可获取 user.id)

- [ ] **Step 1: 在 SeatOverview.vue 模板中添加"我的座位"分区**

在 `<template>` 中，找到 `<div class="filters">` 的结束标签 `</div>` 之后（第 33 行后），在 `<div class="seat-list">` 之前插入：

```html
<div v-if="myFixedSeat || status.is_checked_in" class="my-seat-section">
  <div class="section-title">我的座位</div>
  <div v-if="status.is_checked_in" class="my-seat-card checked-in-card" @click="goToCheckinBySeatId(status.seat_id)">
    <div class="my-seat-icon">
      <span class="pulse-dot"></span>
    </div>
    <div class="my-seat-info">
      <div class="my-seat-name">{{ status.seat_name }}</div>
      <div class="my-seat-meta">已签到 · {{ formatTime(status.elapsed_minutes) }}</div>
    </div>
    <div class="my-seat-action">签退</div>
  </div>
  <div
    v-if="myFixedSeat && !status.is_checked_in"
    class="my-seat-card fixed-card"
    @click="goToCheckin(myFixedSeat)"
  >
    <div class="my-seat-icon fixed-icon">固定</div>
    <div class="my-seat-info">
      <div class="my-seat-name">{{ myFixedSeat.name }}</div>
      <div class="my-seat-meta">固定座位 · {{ myFixedSeat.seat_type === 'fixed' ? '已分配给你' : '共享' }}</div>
    </div>
    <div class="my-seat-action">签到</div>
  </div>
</div>
```

- [ ] **Step 2: 添加 script 逻辑**

在 `<script setup>` 中，`import api from '../api'` 之后追加 `useAuthStore` 导入：

```javascript
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
```

在 `filteredSeats` computed 之后添加 `myFixedSeat` computed：

```javascript
const myFixedSeat = computed(() => {
  return seats.value.find(s => s.seat_type === 'fixed' && s.assigned_user_id === auth.user?.id) || null
})
```

添加 `goToCheckinBySeatId` 函数：

```javascript
function goToCheckinBySeatId(seatId) {
  const seat = seats.value.find(s => s.id === seatId)
  if (seat) goToCheckin(seat)
}
```

- [ ] **Step 3: 添加 CSS 样式**

在 `<style scoped>` 末尾追加：

```css
.my-seat-section {
  margin-bottom: 1rem;
}
.section-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: #999;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.my-seat-card {
  display: flex;
  align-items: center;
  background: white;
  border-radius: 10px;
  padding: 0.875rem 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  cursor: pointer;
  gap: 0.75rem;
}
.my-seat-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.my-seat-card.checked-in-card {
  border-left: 4px solid #4caf50;
}
.my-seat-card.fixed-card {
  border-left: 4px solid #2196f3;
}
.my-seat-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e8f5e9;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.my-seat-icon.fixed-icon {
  background: #e3f2fd;
  color: #1565c0;
  font-size: 0.7rem;
  font-weight: bold;
}
.pulse-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #4caf50;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.my-seat-info {
  flex: 1;
  min-width: 0;
}
.my-seat-name {
  font-weight: 600;
  font-size: 0.95rem;
}
.my-seat-meta {
  font-size: 0.75rem;
  color: #999;
}
.my-seat-action {
  font-size: 0.8rem;
  color: #4caf50;
  font-weight: 500;
  flex-shrink: 0;
}
```

- [ ] **Step 4: 启动前端验证**

```bash
cd frontend && npm run dev
```

验证场景：
1. 有固定座位 + 未签到 → 显示固定座位卡片（蓝色左边框）
2. 已签到 → 显示签到座位卡片（绿色左边框 + 脉冲动画）
3. 有固定座位 + 已签到 → 两个卡片都显示
4. 无固定座位 + 未签到 → 不显示此分区

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/SeatOverview.vue
git commit -m "feat: prioritize own seat display in seat overview"
```

---

### Task 4: 布局对齐修复

**Files:**
- Modify: `frontend/src/components/NavBar.vue` (用户名截断)
- Modify: `frontend/src/views/Admin.vue` (row-info / row-actions 对齐)
- Modify: `frontend/src/views/SeatOverview.vue` (seat-status 固定宽度)

- [ ] **Step 1: 修复 NavBar.vue 用户名对齐**

在 `NavBar.vue` 的 `<style scoped>` 中找到 `.nav-user span`（不存在则在 `.nav-user` 之后新增）：

```css
.nav-user span {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

- [ ] **Step 2: 修复 Admin.vue 行对齐**

在 `Admin.vue` 的 `<style scoped>` 中修改 `.row-info`：

```css
.row-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}
```

修改 `.row-info strong`：

```css
.row-info strong {
  display: block;
  font-size: 0.95rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

修改 `.row-actions`：

```css
.row-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}
```

- [ ] **Step 3: 修复 SeatOverview.vue 座位状态对齐**

在 `SeatOverview.vue` 的 `<style scoped>` 中修改 `.seat-status`：

```css
.seat-status {
  font-size: 0.8rem;
  flex-shrink: 0;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

- [ ] **Step 4: 启动前端验证所有页面对齐**

在浏览器中依次检查：
1. NavBar：长用户名不推挤按钮位置
2. Admin 用户列表：多按钮不挤压左侧名称
3. Admin 座位列表：5 个按钮行不挤压左侧名称
4. SeatOverview：占用者长名字不破坏行布局

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/NavBar.vue frontend/src/views/Admin.vue frontend/src/views/SeatOverview.vue
git commit -m "fix: align usernames and actions across all pages"
```
