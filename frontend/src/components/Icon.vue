<template>
  <svg class="icon" :class="`icon--${size}`" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path v-if="name === 'dashboard'" d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" />
    <path v-else-if="name === 'market'" d="M4 10h16M5 10v9h14v-9M7 10V7l5-3 5 3v3M8 14h8M8 17h5" />
    <path v-else-if="name === 'team'" d="M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-3A3.5 3.5 0 0 0 6 18.5V20M11 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM17 11a2.5 2.5 0 1 0 0-5M18 15a3 3 0 0 1 3 3v2" />
    <path v-else-if="name === 'clock'" d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 7v5l3 2" />
    <path v-else-if="name === 'map'" d="m4 6 5-2 6 2 5-2v14l-5 2-6-2-5 2V6ZM9 4v14M15 6v14" />
    <path v-else-if="name === 'spark'" d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3ZM19 16l.7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z" />
    <path v-else-if="name === 'wallet'" d="M4 7.5A2.5 2.5 0 0 1 6.5 5H19v14H6.5A2.5 2.5 0 0 1 4 16.5v-9ZM4 8h15M16 12h3v3h-3a1.5 1.5 0 0 1 0-3Z" />
    <path v-else-if="name === 'arrow'" d="M5 12h14M13 6l6 6-6 6" />
    <path v-else-if="name === 'check'" d="m5 12 4 4L19 6" />
    <path v-else-if="name === 'alert'" d="M12 4 3.5 19h17L12 4ZM12 10v4M12 17h.01" />
    <path v-else d="M12 3v18M3 12h18" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ name: string; size?: 'sm' | 'md' | 'lg' }>(), { size: 'md' })
</script>

