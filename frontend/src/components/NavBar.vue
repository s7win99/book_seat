<template>
  <nav class="navbar">
    <div class="nav-brand">QFNUACM实验室出勤系统</div>
    <div class="nav-links">
      <router-link to="/">座位</router-link>
      <router-link to="/attendance">我的出勤</router-link>
      <router-link to="/leaderboard">排行榜</router-link>
      <router-link v-if="auth.isAdmin" to="/admin">管理</router-link>
    </div>
    <div class="nav-user">
      <span>{{ auth.user?.name }}</span>
      <button @click="showPasswordModal = true">修改密码</button>
      <button @click="handleLogout">退出</button>
    </div>
  </nav>

  <!-- Change Password Modal -->
  <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false">
    <div class="modal">
      <h3>修改密码</h3>
      <input v-model="oldPassword" type="password" placeholder="当前密码" />
      <input v-model="newPassword" type="password" placeholder="新密码" />
      <input v-model="confirmPassword" type="password" placeholder="确认新密码" />
      <p v-if="passwordError" class="error">{{ passwordError }}</p>
      <p v-if="passwordSuccess" class="success">{{ passwordSuccess }}</p>
      <div class="modal-actions">
        <button class="cancel" @click="showPasswordModal = false">取消</button>
        <button @click="handleChangePassword">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import api from '../api'

const auth = useAuthStore()
const router = useRouter()

const showPasswordModal = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')
const passwordSuccess = ref('')

function handleLogout() {
  auth.logout()
  router.push('/login')
}

async function handleChangePassword() {
  passwordError.value = ''
  passwordSuccess.value = ''

  if (!oldPassword.value || !newPassword.value || !confirmPassword.value) {
    passwordError.value = '请填写所有字段'
    return
  }
  if (newPassword.value.length < 6) {
    passwordError.value = '新密码至少6位'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = '两次密码不一致'
    return
  }

  try {
    await api.post('/api/auth/change-password', {
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    passwordSuccess.value = '密码修改成功！'
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    setTimeout(() => {
      showPasswordModal.value = false
      passwordSuccess.value = ''
    }, 1500)
  } catch (e) {
    passwordError.value = e.response?.data?.detail || '修改密码失败'
  }
}
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  padding: 0.75rem 1.5rem;
  background: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  gap: 1.5rem;
}
.nav-brand {
  font-weight: bold;
  font-size: 1.125rem;
  color: #4caf50;
}
.nav-links {
  display: flex;
  gap: 1rem;
  flex: 1;
}
.nav-links a {
  text-decoration: none;
  color: #666;
  font-size: 0.875rem;
}
.nav-links a.router-link-active {
  color: #4caf50;
  font-weight: bold;
}
.nav-user {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.875rem;
}
.nav-user span {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nav-user button {
  padding: 0.375rem 0.75rem;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.modal h3 {
  margin: 0;
}
.modal input {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 0.9rem;
}
.modal-actions {
  display: flex;
  gap: 0.5rem;
}
.modal-actions button {
  flex: 1;
  padding: 0.75rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  background: #4caf50;
  color: white;
}
.modal-actions button.cancel {
  background: #f5f5f5;
  color: #666;
}
.error {
  color: #e53935;
  font-size: 0.8rem;
  margin: 0;
}
.success {
  color: #4caf50;
  font-size: 0.8rem;
  margin: 0;
}
</style>
