<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()

onMounted(async () => {
  if (auth.token) {
    try {
      await auth.fetchUser()
    } catch {
      auth.logout()
    }
  }
})
</script>
