<template>
  <div class="money-pouch" aria-label="目前金幣">
    <div class="money-pouch__seal"><Icon name="wallet" size="sm" /></div>
    <div>
      <span class="money-pouch__label">金錢袋</span>
      <strong>{{ amount.toLocaleString() }} <small>枚</small></strong>
    </div>
  </div>
</template>

<script setup lang="ts">
import Icon from '@/components/Icon.vue'

defineProps<{ amount: number }>()
</script>

