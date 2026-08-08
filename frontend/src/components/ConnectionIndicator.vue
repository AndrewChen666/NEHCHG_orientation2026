<template>
  <span class="connection-indicator" :class="{ 'is-demo': demo, 'is-offline': !connected }">
    <span class="connection-dot" />
    {{ demo ? '展示資料' : connected ? '即時同步中' : '等待連線' }}
  </span>
</template>

<script setup lang="ts">
defineProps<{ connected: boolean; demo?: boolean }>()
</script>

