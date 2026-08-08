<template>
  <div class="period-clock">
    <div class="period-clock__icon"><Icon name="clock" size="sm" /></div>
    <div>
      <span class="period-clock__label">第 {{ period || '—' }} 時段</span>
      <strong>{{ formatted }}</strong>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import Icon from '@/components/Icon.vue'
import type { SessionStatus } from '@/types/game'

const props = defineProps<{ period: number; elapsedMs: number; status: SessionStatus }>()
const now = ref(Date.now())
const runningSince = ref(Date.now() - props.elapsedMs)
let timer: number | undefined

onMounted(() => {
  timer = window.setInterval(() => { now.value = Date.now() }, 1000)
})
onBeforeUnmount(() => { if (timer) window.clearInterval(timer) })

const elapsed = computed(() => {
  const base = props.status === 'running' ? now.value - runningSince.value : props.elapsedMs
  return Math.max(0, Math.floor(base / 1000))
})
const formatted = computed(() => {
  const minutes = Math.floor(elapsed.value / 60)
  const seconds = elapsed.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})
</script>
