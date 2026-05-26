<template>
  <div>
    <NavBar />
    <div class="container">
      <div v-if="status.is_checked_in" class="status-card checked-in">
        <div class="status-info">
          <h3>已签到</h3>
          <p>座位：{{ status.seat_name }}</p>
          <p>已用：{{ formatTime(status.elapsed_minutes) }}</p>
        </div>
        <div class="today-total">
          <span class="label">今日累计</span>
          <span class="value">{{ formatTime(status.today_total_minutes) }}</span>
        </div>
      </div>
      <div v-else class="status-card">
        <p>未签到</p>
        <p class="today-info">今日：{{ formatTime(status.today_total_minutes) }}</p>
      </div>

      <div class="filters">
        <button
          v-for="f in filterOptions"
          :key="f.key"
          :class="{ active: filter === f.key }"
          @click="filter = f.key"
        >
          {{ f.label }}
          <span v-if="f.key === 'all'">({{ seats.length }})</span>
          <span v-if="f.key === 'free'">({{ freeCount }})</span>
          <span v-if="f.key === 'occupied'">({{ occupiedCount }})</span>
        </button>
      </div>

      <div v-if="myFixedSeat || status.is_checked_in" class="my-seat-section">
        <div class="my-seat-section-title">我的座位</div>
        <div v-if="status.is_checked_in" class="my-seat-card checked-in-card" @click="goToCheckinBySeatId(status.seat_id)">
          <div class="my-seat-icon">
            <span class="pulse-dot"></span>
          </div>
          <div class="my-seat-info">
            <div class="my-seat-name">{{ status.seat_name }}</div>
            <div class="my-seat-meta">已签到 · {{ formatTime(status.elapsed_minutes) }}</div>
          </div>
          <div class="my-seat-action">前往</div>
        </div>
        <div
          v-if="myFixedSeat && !status.is_checked_in"
          class="my-seat-card fixed-card"
          @click="goToCheckin(myFixedSeat)"
        >
          <div class="my-seat-icon fixed-icon">固定</div>
          <div class="my-seat-info">
            <div class="my-seat-name">{{ myFixedSeat.name }}</div>
            <div class="my-seat-meta">固定座位</div>
          </div>
          <div class="my-seat-action">签到</div>
        </div>
      </div>

      <div class="seat-list">
        <div
          v-for="seat in filteredSeats"
          :key="seat.id"
          class="seat-row"
          @click="goToCheckin(seat)"
        >
          <div class="seat-icon" :class="seat.is_occupied ? 'occupied' : 'free'">
            {{ seat.name }}
          </div>
          <div class="seat-info">
            <div class="seat-name">{{ seat.name }}</div>
            <div class="seat-meta">
              {{ seat.seat_type === 'fixed' ? '固定' : '共享' }}
              <span v-if="seat.assigned_user_name"> · {{ seat.assigned_user_name }}</span>
            </div>
          </div>
          <div class="seat-status">
            <span v-if="seat.is_occupied" class="status-occupied">{{ seat.occupant_name }}</span>
            <span v-else class="status-free">空闲</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import NavBar from '../components/NavBar.vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const auth = useAuthStore()

const router = useRouter()
const seats = ref([])
const status = ref({ is_checked_in: false, today_total_minutes: 0 })
const filter = ref('all')

const filterOptions = [
  { key: 'all', label: '全部' },
  { key: 'free', label: '空闲' },
  { key: 'occupied', label: '占用' },
]

const freeCount = computed(() => seats.value.filter(s => !s.is_occupied).length)
const occupiedCount = computed(() => seats.value.filter(s => s.is_occupied).length)

const filteredSeats = computed(() => {
  if (filter.value === 'free') return seats.value.filter(s => !s.is_occupied)
  if (filter.value === 'occupied') return seats.value.filter(s => s.is_occupied)
  return seats.value
})

const myFixedSeat = computed(() => {
  return seats.value.find(s => s.seat_type === 'fixed' && s.assigned_user_id === auth.user?.id) || null
})

function formatTime(minutes) {
  if (!minutes) return '0min'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h > 0 ? `${h}h ${m}min` : `${m}min`
}

function goToCheckin(seat) {
  router.push(`/checkin?token=${seat.token}`)
}

function goToCheckinBySeatId(seatId) {
  const seat = seats.value.find(s => s.id === seatId)
  if (seat) {
    goToCheckin(seat)
  } else {
    router.push('/')
  }
}

onMounted(async () => {
  const [seatsRes, statusRes] = await Promise.all([
    api.get('/api/seats'),
    api.get('/api/checkin/status'),
  ])
  seats.value = seatsRes.data
  status.value = statusRes.data
})
</script>

<style scoped>
.container {
  max-width: 640px;
  margin: 0 auto;
  padding: 1rem;
}
.status-card {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  margin-bottom: 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.status-card.checked-in {
  border-left: 4px solid #4caf50;
}
.status-info h3 {
  margin: 0 0 0.25rem;
  color: #4caf50;
}
.status-info p {
  margin: 0;
  font-size: 0.875rem;
  color: #666;
}
.today-total {
  text-align: center;
}
.today-total .label {
  display: block;
  font-size: 0.75rem;
  color: #999;
}
.today-total .value {
  font-size: 1.25rem;
  font-weight: bold;
  color: #333;
}
.today-info {
  color: #666;
  font-size: 0.875rem;
}
.filters {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.filters button {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: white;
  cursor: pointer;
  font-size: 0.8rem;
}
.filters button.active {
  background: #4caf50;
  color: white;
  border-color: #4caf50;
}
.seat-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.seat-row {
  display: flex;
  align-items: center;
  background: white;
  border-radius: 10px;
  padding: 0.875rem 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  cursor: pointer;
  gap: 1rem;
}
.seat-row:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.seat-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: bold;
}
.seat-icon.free {
  background: #f5f5f5;
  color: #999;
}
.seat-icon.occupied {
  background: #e8f5e9;
  color: #2e7d32;
}
.seat-info {
  flex: 1;
}
.seat-name {
  font-weight: 600;
  font-size: 0.95rem;
}
.seat-meta {
  font-size: 0.75rem;
  color: #999;
}
.seat-status {
  font-size: 0.8rem;
}
.status-occupied {
  color: #4caf50;
  font-weight: 500;
}
.status-free {
  color: #ccc;
}
.my-seat-section {
  margin-bottom: 1rem;
}
.my-seat-section-title {
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
</style>
