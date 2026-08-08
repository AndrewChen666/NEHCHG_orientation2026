<template>
  <RouterView v-slot="{ Component }">
    <Transition name="page" mode="out-in">
      <component :is="Component" :key="route.fullPath" />
    </Transition>
  </RouterView>
</template>

<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'

const route = useRoute()
</script>
