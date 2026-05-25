<template>
  <nav class="navbar">
    <div class="nav-brand">Lab Seats</div>
    <div class="nav-links">
      <router-link to="/">Seats</router-link>
      <router-link to="/attendance">My Attendance</router-link>
      <router-link to="/leaderboard">Leaderboard</router-link>
      <router-link v-if="auth.isAdmin" to="/admin">Admin</router-link>
    </div>
    <div class="nav-user">
      <span>{{ auth.user?.name }}</span>
      <button @click="handleLogout">Logout</button>
    </div>
  </nav>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/login')
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
.nav-user button {
  padding: 0.375rem 0.75rem;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
}
</style>
