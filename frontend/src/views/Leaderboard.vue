<template>
  <div>
    <NavBar />
    <div class="container">
      <div class="period-toggle">
        <button :class="{ active: period === 'week' }" @click="period = 'week'; load()">This Week</button>
        <button :class="{ active: period === 'month' }" @click="period = 'month'; load()">This Month</button>
      </div>

      <div class="leaderboard">
        <div v-for="(entry, i) in entries" :key="entry.user_id" class="entry-row" :class="{ 'top': i < 3 }">
          <div class="rank" :class="'rank-' + (i + 1)">{{ i + 1 }}</div>
          <div class="name">{{ entry.name }}</div>
          <div class="stats">
            <span class="rate">{{ (entry.attendance_rate * 100).toFixed(1) }}%</span>
            <span class="count">{{ entry.valid_count }} valid</span>
          </div>
        </div>
        <p v-if="entries.length === 0" class="empty">No data yet</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import NavBar from '../components/NavBar.vue'
import api from '../api'

const period = ref('week')
const entries = ref([])

async function load() {
  const res = await api.get(`/api/attendance/leaderboard?period=${period.value}`)
  entries.value = res.data
}

onMounted(load)
</script>

<style scoped>
.container {
  max-width: 480px;
  margin: 0 auto;
  padding: 1rem;
}
.period-toggle {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}
.period-toggle button {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 10px;
  background: white;
  cursor: pointer;
  font-size: 0.9rem;
}
.period-toggle button.active {
  background: #4caf50;
  color: white;
  border-color: #4caf50;
}
.leaderboard {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.entry-row {
  display: flex;
  align-items: center;
  background: white;
  border-radius: 12px;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  gap: 1rem;
}
.entry-row.top {
  border-left: 4px solid #4caf50;
}
.rank {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1rem;
  background: #f5f5f5;
  color: #666;
}
.rank-1 {
  background: #ffd700;
  color: white;
}
.rank-2 {
  background: #c0c0c0;
  color: white;
}
.rank-3 {
  background: #cd7f32;
  color: white;
}
.name {
  flex: 1;
  font-weight: 600;
}
.stats {
  text-align: right;
}
.rate {
  display: block;
  font-size: 1.125rem;
  font-weight: bold;
  color: #4caf50;
}
.count {
  font-size: 0.75rem;
  color: #999;
}
.empty {
  text-align: center;
  color: #999;
  padding: 2rem;
}
</style>
