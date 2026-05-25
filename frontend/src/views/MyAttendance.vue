<template>
  <div>
    <NavBar />
    <div class="container">
      <div class="stats-row">
        <div class="stat-card">
          <span class="stat-value">{{ validCount }}</span>
          <span class="stat-label">有效出勤</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ formatTime(totalMinutes) }}</span>
          <span class="stat-label">总时长</span>
        </div>
      </div>

      <div class="calendar">
        <div class="calendar-header">
          <button @click="prevMonth">&lt;</button>
          <span>{{ monthLabel }}</span>
          <button @click="nextMonth">&gt;</button>
        </div>
        <div class="calendar-weekdays">
          <span v-for="d in ['一','二','三','四','五','六','日']" :key="d">{{ d }}</span>
        </div>
        <div class="calendar-days">
          <span
            v-for="(day, i) in calendarDays"
            :key="i"
            class="day"
            :class="{
              'empty': !day.date,
              'valid': day.valid,
              'weekend': day.isWeekend,
              'today': day.isToday,
            }"
          >
            {{ day.dayNum }}
          </span>
        </div>
      </div>

      <div class="history">
        <h3>签到记录</h3>
        <div v-for="record in records" :key="record.id" class="history-row">
          <span class="date">{{ record.date }}</span>
          <span class="minutes">{{ record.total_minutes }}min</span>
          <span class="badge" :class="record.is_valid ? 'valid' : 'invalid'">
            {{ record.is_valid ? '有效' : '无效' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import NavBar from '../components/NavBar.vue'
import api from '../api'

const records = ref([])
const currentDate = ref(new Date())

const monthLabel = computed(() => {
  return currentDate.value.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })
})

const validCount = computed(() => records.value.filter(r => r.is_valid).length)
const totalMinutes = computed(() => records.value.reduce((sum, r) => sum + r.total_minutes, 0))

const calendarDays = computed(() => {
  const year = currentDate.value.getFullYear()
  const month = currentDate.value.getMonth()
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const days = []
  const startOffset = (firstDay.getDay() + 6) % 7

  for (let i = 0; i < startOffset; i++) {
    days.push({ date: null, dayNum: '' })
  }

  for (let d = 1; d <= lastDay.getDate(); d++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const record = records.value.find(r => r.date === dateStr)
    const dateObj = new Date(year, month, d)
    days.push({
      date: dateStr,
      dayNum: d,
      valid: record?.is_valid || false,
      isWeekend: dateObj.getDay() === 0 || dateObj.getDay() === 6,
      isToday: dateStr === new Date().toISOString().split('T')[0],
    })
  }

  return days
})

function formatTime(minutes) {
  if (!minutes) return '0min'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h > 0 ? `${h}h ${m}min` : `${m}min`
}

function prevMonth() {
  currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() - 1, 1)
}

function nextMonth() {
  currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1, 1)
}

onMounted(async () => {
  const res = await api.get('/api/attendance/my')
  records.value = res.data
})
</script>

<style scoped>
.container {
  max-width: 640px;
  margin: 0 auto;
  padding: 1rem;
}
.stats-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.stat-card {
  flex: 1;
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.stat-value {
  display: block;
  font-size: 1.75rem;
  font-weight: bold;
  color: #4caf50;
}
.stat-label {
  font-size: 0.75rem;
  color: #999;
}
.calendar {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.calendar-header button {
  background: none;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 0.25rem 0.75rem;
  cursor: pointer;
}
.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-size: 0.75rem;
  color: #999;
  margin-bottom: 0.5rem;
}
.calendar-days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.day {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-size: 0.8rem;
}
.day.empty {
  visibility: hidden;
}
.day.valid {
  background: #4caf50;
  color: white;
  font-weight: bold;
}
.day.weekend:not(.valid) {
  color: #ccc;
}
.day.today {
  border: 2px solid #4caf50;
}
.history h3 {
  margin-bottom: 0.75rem;
}
.history-row {
  display: flex;
  align-items: center;
  background: white;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 0.5rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  gap: 1rem;
}
.date {
  flex: 1;
  font-size: 0.875rem;
}
.minutes {
  font-size: 0.875rem;
  color: #666;
}
.badge {
  padding: 0.2rem 0.5rem;
  border-radius: 8px;
  font-size: 0.7rem;
}
.badge.valid {
  background: #e8f5e9;
  color: #2e7d32;
}
.badge.invalid {
  background: #f5f5f5;
  color: #999;
}
</style>
