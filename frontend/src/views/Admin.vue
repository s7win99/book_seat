<template>
  <div>
    <NavBar />
    <div class="container">
      <div class="tabs">
        <button :class="{ active: tab === 'users' }" @click="tab = 'users'">Users</button>
        <button :class="{ active: tab === 'seats' }" @click="tab = 'seats'">Seats</button>
        <button :class="{ active: tab === 'attendance' }" @click="tab = 'attendance'">Attendance</button>
      </div>

      <!-- Users Tab -->
      <div v-if="tab === 'users'">
        <button class="btn-add" @click="showUserForm = true">+ Add User</button>
        <div v-if="showUserForm" class="form-card">
          <input v-model="userForm.username" placeholder="Username" />
          <input v-model="userForm.name" placeholder="Name" />
          <input v-model="userForm.password" placeholder="Password" type="password" />
          <div class="form-actions">
            <button @click="createUser">Save</button>
            <button class="cancel" @click="showUserForm = false">Cancel</button>
          </div>
        </div>
        <div v-for="u in users" :key="u.id" class="list-row">
          <div class="row-info">
            <strong>{{ u.name }}</strong>
            <span class="meta">{{ u.username }} · {{ u.role }}</span>
          </div>
          <div class="row-actions">
            <button @click="resetPassword(u.id)">Reset PW</button>
            <button class="danger" @click="deleteUser(u.id)" v-if="u.role !== 'admin'">Delete</button>
          </div>
        </div>
      </div>

      <!-- Seats Tab -->
      <div v-if="tab === 'seats'">
        <button class="btn-add" @click="showSeatForm = true">+ Add Seat</button>
        <div v-if="showSeatForm" class="form-card">
          <input v-model="seatForm.name" placeholder="Seat Name" />
          <select v-model="seatForm.seat_type">
            <option value="shared">Shared</option>
            <option value="fixed">Fixed</option>
          </select>
          <select v-if="seatForm.seat_type === 'fixed'" v-model="seatForm.assigned_user_id">
            <option :value="null">Select User</option>
            <option v-for="u in users" :key="u.id" :value="u.id">{{ u.name }}</option>
          </select>
          <div class="form-actions">
            <button @click="createSeat">Save</button>
            <button class="cancel" @click="showSeatForm = false">Cancel</button>
          </div>
        </div>
        <div v-for="s in seats" :key="s.id" class="list-row">
          <div class="row-info">
            <strong>{{ s.name }}</strong>
            <span class="meta">{{ s.seat_type }}{{ s.assigned_user_name ? ' · ' + s.assigned_user_name : '' }}</span>
          </div>
          <div class="row-actions">
            <button @click="refreshToken(s.id)">Refresh Token</button>
            <button @click="viewQR(s.id)">QR</button>
            <button class="danger" @click="deleteSeat(s.id)">Delete</button>
          </div>
        </div>
      </div>

      <!-- Attendance Tab -->
      <div v-if="tab === 'attendance'">
        <div class="date-filter">
          <input type="date" v-model="startDate" />
          <span>to</span>
          <input type="date" v-model="endDate" />
          <button @click="loadAttendance">Filter</button>
        </div>
        <div v-for="a in attendance" :key="a.user_id" class="list-row">
          <div class="row-info">
            <strong>{{ a.name }}</strong>
            <span class="meta">Valid: {{ a.total_valid }} · Total: {{ a.total_minutes }}min</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import NavBar from '../components/NavBar.vue'
import api from '../api'

const tab = ref('users')
const users = ref([])
const seats = ref([])
const attendance = ref([])
const showUserForm = ref(false)
const showSeatForm = ref(false)
const userForm = ref({ username: '', name: '', password: '' })
const seatForm = ref({ name: '', seat_type: 'shared', assigned_user_id: null })
const startDate = ref('')
const endDate = ref('')

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
  if (!confirm('Delete this user?')) return
  await api.delete(`/api/admin/users/${id}`)
  await loadUsers()
}

async function resetPassword(id) {
  await api.post(`/api/admin/users/${id}/reset-password`)
  alert('Password reset to 123456')
}

async function createSeat() {
  await api.post('/api/admin/seats', seatForm.value)
  showSeatForm.value = false
  seatForm.value = { name: '', seat_type: 'shared', assigned_user_id: null }
  await loadSeats()
}

async function deleteSeat(id) {
  if (!confirm('Delete this seat?')) return
  await api.delete(`/api/admin/seats/${id}`)
  await loadSeats()
}

async function refreshToken(id) {
  await api.post(`/api/admin/seats/${id}/refresh-token`)
  await loadSeats()
}

async function viewQR(id) {
  const token = localStorage.getItem('token')
  window.open(`http://localhost:8000/api/admin/seats/${id}/qrcode`, '_blank')
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
