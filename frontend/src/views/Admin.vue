<template>
  <div>
    <NavBar />
    <div class="container">
      <div class="tabs">
        <button :class="{ active: tab === 'users' }" @click="tab = 'users'">用户管理</button>
        <button :class="{ active: tab === 'seats' }" @click="tab = 'seats'">座位管理</button>
        <button :class="{ active: tab === 'attendance' }" @click="tab = 'attendance'">出勤统计</button>
      </div>

      <!-- Users Tab -->
      <div v-if="tab === 'users'">
        <button class="btn-add" @click="showUserForm = true">+ 添加用户</button>
        <div v-if="showUserForm" class="form-card">
          <input v-model="userForm.username" placeholder="用户名" />
          <input v-model="userForm.name" placeholder="姓名" />
          <input v-model="userForm.password" placeholder="密码" type="password" />
          <div class="form-actions">
            <button @click="createUser">保存</button>
            <button class="cancel" @click="showUserForm = false">取消</button>
          </div>
        </div>
        <div v-for="u in users" :key="u.id" class="list-row">
          <div class="row-info">
            <strong>{{ u.name }}</strong>
            <span class="meta">{{ u.username }} · {{ roleLabel(u.role) }}</span>
          </div>
          <div class="row-actions">
            <select
              v-if="auth.isSuperAdmin && u.id !== auth.user?.id"
              :value="u.role"
              @change="changeRole(u.id, $event.target.value)"
              class="role-select"
            >
              <option value="user">用户</option>
              <option value="admin">管理员</option>
              <option value="superadmin">超级管理员</option>
            </select>
            <button @click="resetPassword(u.id)">重置密码</button>
            <button class="danger" @click="deleteUser(u.id)" v-if="u.role !== 'superadmin' || auth.isSuperAdmin">删除</button>
          </div>
        </div>
      </div>

      <!-- Seats Tab -->
      <div v-if="tab === 'seats'">
        <div class="seat-actions">
          <button class="btn-add" @click="showSeatForm = true; editingSeatId = null; seatForm = { name: '', seat_type: 'shared', assigned_user_id: null }">+ 添加座位</button>
          <button class="btn-batch" @click="refreshAllTokens">刷新全部Token</button>
          <button class="btn-batch" @click="exportAllQR">导出全部二维码</button>
        </div>
        <div v-if="showSeatForm" class="form-card">
          <input v-model="seatForm.name" placeholder="座位名称" />
          <select v-model="seatForm.seat_type" @change="onSeatTypeChange">
            <option value="shared">共享</option>
            <option value="fixed">固定</option>
          </select>
          <div v-if="seatForm.seat_type === 'fixed'" class="user-search">
            <input
              v-model="userSearch"
              placeholder="输入用户名或姓名搜索"
              @input="showUserSuggestions = true"
              @focus="showUserSuggestions = true"
            />
            <div v-if="showUserSuggestions && filteredUsers.length > 0" class="suggestions">
              <div
                v-for="u in filteredUsers"
                :key="u.id"
                class="suggestion-item"
                @mousedown.prevent="selectUser(u)"
              >
                {{ u.name }} ({{ u.username }})
              </div>
            </div>
          </div>
          <p v-if="seatForm.seat_type === 'fixed' && seatForm.assigned_user_id" class="selected-user">
            已选：{{ userSearch }}
            <button class="clear-btn" @click="clearSelectedUser">×</button>
          </p>
          <div class="form-actions">
            <button @click="editingSeatId ? updateSeat() : createSeat()">{{ editingSeatId ? '更新' : '保存' }}</button>
            <button class="cancel" @click="showSeatForm = false; editingSeatId = null">取消</button>
          </div>
        </div>
        <div v-for="s in seats" :key="s.id" class="list-row">
          <div class="row-info">
            <strong>{{ s.name }}</strong>
            <span class="meta">{{ s.seat_type === 'fixed' ? '固定' : '共享' }}{{ s.assigned_user_name ? ' · ' + s.assigned_user_name : '' }}</span>
          </div>
          <div class="row-actions">
            <button @click="editSeat(s)">编辑</button>
            <button @click="refreshToken(s.id)">刷新Token</button>
            <button @click="viewQR(s.id)">二维码</button>
            <button v-if="s.is_occupied" class="warning" @click="cancelCheckin(s)">取消签到</button>
            <button class="danger" @click="deleteSeat(s.id)">删除</button>
          </div>
        </div>
      </div>

      <!-- Attendance Tab -->
      <div v-if="tab === 'attendance'">
        <div class="date-filter">
          <input type="date" v-model="startDate" />
          <span>至</span>
          <input type="date" v-model="endDate" />
          <button @click="loadAttendance">筛选</button>
        </div>
        <div v-for="a in attendance" :key="a.user_id" class="list-row">
          <div class="row-info">
            <strong>{{ a.name }}</strong>
            <span class="meta">有效：{{ a.total_valid }} · 总时长：{{ a.total_minutes }}min</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import NavBar from '../components/NavBar.vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const auth = useAuthStore()

const tab = ref('users')
const users = ref([])
const seats = ref([])
const attendance = ref([])
const showUserForm = ref(false)
const showSeatForm = ref(false)
const editingSeatId = ref(null)
const userForm = ref({ username: '', name: '', password: '' })
const seatForm = ref({ name: '', seat_type: 'shared', assigned_user_id: null })
const userSearch = ref('')
const showUserSuggestions = ref(false)
const startDate = ref('')
const endDate = ref('')

const filteredUsers = computed(() => {
  const q = userSearch.value.toLowerCase().trim()
  if (!q) return users.value
  return users.value.filter(u =>
    u.username.toLowerCase().includes(q) || u.name.toLowerCase().includes(q)
  )
})

function selectUser(user) {
  seatForm.value.assigned_user_id = user.id
  userSearch.value = `${user.name} (${user.username})`
  showUserSuggestions.value = false
}

function clearSelectedUser() {
  seatForm.value.assigned_user_id = null
  userSearch.value = ''
}

function onSeatTypeChange() {
  if (seatForm.value.seat_type === 'shared') {
    seatForm.value.assigned_user_id = null
    userSearch.value = ''
  }
}

function roleLabel(role) {
  if (role === 'superadmin') return '超级管理员'
  if (role === 'admin') return '管理员'
  return '用户'
}

async function changeRole(userId, newRole) {
  try {
    await api.put(`/api/admin/users/${userId}/role?role=${newRole}`)
    await loadUsers()
  } catch (e) {
    alert(e.response?.data?.detail || '修改角色失败')
  }
}

async function loadUsers() {
  const res = await api.get('/api/admin/users')
  users.value = res.data
}

async function loadSeats() {
  const res = await api.get('/api/admin/seats')
  seats.value = res.data
}

async function loadAttendance() {
  let url = '/api/admin/attendance'
  const params = []
  if (startDate.value) params.push(`start_date=${startDate.value}`)
  if (endDate.value) params.push(`end_date=${endDate.value}`)
  if (params.length) url += '?' + params.join('&')
  const res = await api.get(url)
  attendance.value = res.data
}

async function createUser() {
  await api.post('/api/admin/users', userForm.value)
  showUserForm.value = false
  userForm.value = { username: '', name: '', password: '' }
  await loadUsers()
}

async function deleteUser(id) {
  if (!confirm('确定删除该用户？')) return
  await api.delete(`/api/admin/users/${id}`)
  await loadUsers()
}

async function resetPassword(id) {
  await api.post(`/api/admin/users/${id}/reset-password`)
  alert('密码已重置为 123456')
}

async function createSeat() {
  await api.post('/api/admin/seats', seatForm.value)
  showSeatForm.value = false
  seatForm.value = { name: '', seat_type: 'shared', assigned_user_id: null }
  await loadSeats()
}

function editSeat(seat) {
  editingSeatId.value = seat.id
  seatForm.value = {
    name: seat.name,
    seat_type: seat.seat_type,
    assigned_user_id: seat.assigned_user_id,
  }
  if (seat.seat_type === 'fixed' && seat.assigned_user_name) {
    userSearch.value = seat.assigned_user_name
  } else {
    userSearch.value = ''
  }
  showSeatForm.value = true
}

async function updateSeat() {
  await api.put(`/api/admin/seats/${editingSeatId.value}`, seatForm.value)
  showSeatForm.value = false
  editingSeatId.value = null
  seatForm.value = { name: '', seat_type: 'shared', assigned_user_id: null }
  await loadSeats()
}

async function deleteSeat(id) {
  if (!confirm('确定删除该座位？')) return
  await api.delete(`/api/admin/seats/${id}`)
  await loadSeats()
}

async function refreshToken(id) {
  await api.post(`/api/admin/seats/${id}/refresh-token`)
  await loadSeats()
}

async function refreshAllTokens() {
  if (!confirm('确定刷新全部座位的Token？刷新后旧二维码将失效。')) return
  try {
    await api.post('/api/admin/seats/refresh-all-tokens')
    alert('全部Token已刷新')
    await loadSeats()
  } catch (e) {
    alert('刷新失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function exportAllQR() {
  try {
    const res = await api.get('/api/admin/seats/qrcode-batch', { responseType: 'blob' })
    const contentType = res.headers['content-type']
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    if (contentType && contentType.includes('zip')) {
      a.download = '座位二维码.zip'
    } else {
      a.download = '座位二维码.png'
    }
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('导出失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function cancelCheckin(seat) {
  if (!confirm(`确定取消 ${seat.occupant_name} 的签到？该段签到时间将不被记录。`)) return
  try {
    await api.post(`/api/admin/cancel-checkin/${seat.occupant_user_id}`)
    await loadSeats()
  } catch (e) {
    alert(e.response?.data?.detail || '取消签到失败')
  }
}

async function viewQR(id) {
  const res = await api.get(`/api/admin/seats/${id}/qrcode`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  window.open(url, '_blank')
}

onMounted(() => {
  loadUsers()
  loadSeats()
  loadAttendance()
})
</script>

<style scoped>
.container {
  max-width: 640px;
  margin: 0 auto;
  padding: 1rem;
}
.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}
.tabs button {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 10px;
  background: white;
  cursor: pointer;
}
.tabs button.active {
  background: #4caf50;
  color: white;
  border-color: #4caf50;
}
.btn-add {
  width: 100%;
  padding: 0.75rem;
  background: #e8f5e9;
  color: #2e7d32;
  border: 2px dashed #4caf50;
  border-radius: 10px;
  cursor: pointer;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}
.seat-actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.seat-actions .btn-add {
  flex: 1;
  margin-bottom: 0;
}
.btn-batch {
  padding: 0.75rem 1rem;
  background: #e3f2fd;
  color: #1565c0;
  border: 1px solid #90caf9;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.9rem;
}
.form-card {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  margin-bottom: 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.form-card input, .form-card select {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 0.9rem;
}
.user-search {
  position: relative;
}
.user-search input {
  width: 100%;
  box-sizing: border-box;
}
.suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-top: none;
  border-radius: 0 0 8px 8px;
  max-height: 150px;
  overflow-y: auto;
  z-index: 10;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.suggestion-item {
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  font-size: 0.85rem;
}
.suggestion-item:hover {
  background: #f5f5f5;
}
.selected-user {
  font-size: 0.8rem;
  color: #4caf50;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.clear-btn {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 1rem;
  padding: 0;
  line-height: 1;
}
.clear-btn:hover {
  color: #e53935;
}
.form-actions {
  display: flex;
  gap: 0.5rem;
}
.form-actions button {
  flex: 1;
  padding: 0.75rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  background: #4caf50;
  color: white;
}
.form-actions button.cancel {
  background: #f5f5f5;
  color: #666;
}
.list-row {
  display: flex;
  align-items: center;
  background: white;
  padding: 0.875rem 1rem;
  border-radius: 10px;
  margin-bottom: 0.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.row-info {
  flex: 1;
}
.row-info strong {
  display: block;
  font-size: 0.95rem;
}
.row-info .meta {
  font-size: 0.75rem;
  color: #999;
}
.row-actions {
  display: flex;
  gap: 0.5rem;
}
.row-actions button {
  padding: 0.375rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 0.75rem;
}
.row-actions button.danger {
  color: #e53935;
  border-color: #e53935;
}
.row-actions button.warning {
  color: #e65100;
  border-color: #e65100;
}
.role-select {
  padding: 0.375rem 0.5rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.75rem;
  background: white;
  cursor: pointer;
}
.date-filter {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 1rem;
}
.date-filter input {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}
.date-filter button {
  padding: 0.5rem 1rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
</style>
