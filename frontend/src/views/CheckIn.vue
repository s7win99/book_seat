<template>
  <div>
    <NavBar />
    <div class="container">
      <div v-if="loading" class="loading">Loading...</div>
      <div v-else-if="error" class="error-card">
        <p>{{ error }}</p>
        <button @click="$router.push('/')">Back to Seats</button>
      </div>
      <div v-else class="checkin-card">
        <h2>{{ seatInfo.name }}</h2>
        <span class="badge" :class="seatInfo.seat_type">
          {{ seatInfo.seat_type === 'fixed' ? 'Fixed' : 'Shared' }}
        </span>

        <div v-if="seatInfo.is_occupied && !isMySeat" class="message occupied">
          Occupied by {{ seatInfo.occupant_name }}
        </div>

        <div v-else-if="seatInfo.seat_type === 'fixed' && !isAssignedToMe" class="message reserved">
          This seat is reserved for {{ seatInfo.assigned_user_name }}
        </div>

        <div v-else-if="hasFixedSeat && seatInfo.seat_type === 'shared'" class="message reserved">
          You have a fixed seat, please check in there
        </div>

        <div v-else-if="cooldownRemaining > 0" class="message cooldown">
          Cooldown: please wait {{ cooldownRemaining }} seconds
        </div>

        <div v-else-if="isMySeat" class="action-section">
          <div class="elapsed">
            <span class="label">Elapsed Time</span>
            <span class="time">{{ formatTime(elapsedMinutes) }}</span>
          </div>
          <button class="btn checkout" @click="handleCheckout">Confirm Check-out</button>
        </div>

        <div v-else-if="isAlreadyCheckedIn" class="action-section">
          <div class="switch-info">
            <p>You are currently at seat <strong>{{ currentSeatName }}</strong></p>
            <p>Switch to {{ seatInfo.name }}?</p>
          </div>
          <button class="btn switch" @click="handleCheckin">Switch to this seat</button>
        </div>

        <div v-else class="action-section">
          <button class="btn checkin" @click="handleCheckin">Confirm Check-in</button>
        </div>

        <button class="back-link" @click="$router.push('/')">Back to Seats</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import NavBar from '../components/NavBar.vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const seatInfo = ref(null)
const loading = ref(true)
const error = ref('')
const cooldownRemaining = ref(0)
const elapsedMinutes = ref(0)
const currentSeatName = ref('')

const isMySeat = computed(() => seatInfo.value?.current_user_checked_in && seatInfo.value?.current_user_seat_id === seatInfo.value?.id)
const isAlreadyCheckedIn = computed(() => seatInfo.value?.current_user_checked_in && seatInfo.value?.current_user_seat_id !== seatInfo.value?.id)
const isAssignedToMe = computed(() => seatInfo.value?.assigned_user_id === auth.user?.id)
const hasFixedSeat = computed(() => {
  return seatInfo.value?.seat_type === 'shared' && auth.user?.role === 'user'
})

function formatTime(minutes) {
  if (!minutes) return '0min'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h > 0 ? `${h}h ${m}min` : `${m}min`
}

async function loadSeatInfo() {
  try {
    const token = route.query.token
    if (!token) {
      error.value = 'No seat token provided'
      return
    }
    const res = await api.get(`/api/seats/by-token/${token}`)
    seatInfo.value = res.data
    cooldownRemaining.value = res.data.cooldown_remaining || 0

    if (res.data.current_user_checked_in) {
      const statusRes = await api.get('/api/checkin/status')
      if (statusRes.data.is_checked_in) {
        elapsedMinutes.value = statusRes.data.elapsed_minutes
        currentSeatName.value = statusRes.data.seat_name
      }
    }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load seat info'
  } finally {
    loading.value = false
  }
}

async function handleCheckin() {
  try {
    await api.post('/api/checkin', { seat_token: route.query.token })
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Check-in failed'
    if (e.response?.status === 429) {
      cooldownRemaining.value = parseInt(e.response.data.detail.match(/\d+/)?.[0] || 60)
    }
  }
}

async function handleCheckout() {
  try {
    await api.post('/api/checkout', { seat_id: seatInfo.value.id })
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Check-out failed'
  }
}

onMounted(loadSeatInfo)
</script>

<style scoped>
.container {
  max-width: 480px;
  margin: 0 auto;
  padding: 1.5rem;
}
.checkin-card {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  text-align: center;
}
h2 {
  margin: 0 0 0.5rem;
}
.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  margin-bottom: 1.5rem;
}
.badge.fixed {
  background: #e3f2fd;
  color: #1565c0;
}
.badge.shared {
  background: #f5f5f5;
  color: #666;
}
.message {
  padding: 1rem;
  border-radius: 10px;
  margin-bottom: 1.5rem;
  font-size: 0.9rem;
}
.message.occupied {
  background: #fff3e0;
  color: #e65100;
}
.message.reserved {
  background: #fce4ec;
  color: #c62828;
}
.message.cooldown {
  background: #f3e5f5;
  color: #6a1b9a;
}
.action-section {
  margin-bottom: 1.5rem;
}
.elapsed {
  margin-bottom: 1rem;
}
.elapsed .label {
  display: block;
  font-size: 0.75rem;
  color: #999;
  margin-bottom: 0.25rem;
}
.elapsed .time {
  font-size: 2rem;
  font-weight: bold;
  color: #4caf50;
}
.switch-info {
  margin-bottom: 1rem;
  font-size: 0.9rem;
  color: #666;
}
.btn {
  width: 100%;
  padding: 1rem;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}
.btn.checkin {
  background: #4caf50;
  color: white;
}
.btn.checkout {
  background: #ff9800;
  color: white;
}
.btn.switch {
  background: #2196f3;
  color: white;
}
.btn:hover {
  opacity: 0.9;
}
.back-link {
  display: block;
  margin-top: 1rem;
  color: #999;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
}
.loading, .error-card {
  text-align: center;
  padding: 2rem;
}
.error-card button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}
</style>
