<template>
  <div class="app-frame" :class="{ 'is-ceremonial': props.variant === 'ceremonial' }">
    <main class="main-stage">
      <header class="topbar">
        <div class="topbar-brand">
          <RouterLink class="brand-lockup" to="/" aria-label="回到活米村首頁">
            <img class="brand-mark" src="/icon.png" alt="" aria-hidden="true" />
            <span class="brand-lockup__text"><strong>活米村</strong><small>現場控制台</small></span>
          </RouterLink>
          <span class="topbar-divider" aria-hidden="true" />
          <div class="topbar-role"><span>{{ roleLabel }}</span><strong>{{ identity }}</strong></div>
        </div>

        <nav v-if="navItems.length" class="top-nav" aria-label="工作板導覽">
          <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="top-nav__link" :class="{ 'is-active': route.path === item.to }">{{ item.label }}</RouterLink>
        </nav>

        <div class="topbar-actions">
          <div class="topbar-status" aria-label="遊戲狀態">
            <ConnectionIndicator :connected="connected" :demo="demo" />
            <PeriodClock :period="period" :elapsed-ms="elapsedMs" :status="status" />
            <MoneyPouch :amount="money" />
          </div>
          <slot name="heading-actions" />
          <button class="topbar-exit" type="button" @click="$emit('signOut')">離開</button>
        </div>
      </header>

      <div class="page-wrap">
        <section v-if="!hidePageHeading" class="page-heading">
          <div>
            <span class="page-heading__context">{{ section }}・現場工作板</span>
            <h1>{{ title }}</h1>
            <p>{{ subtitle }}</p>
          </div>
        </section>
        <div class="page-content"><slot /></div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import ConnectionIndicator from '@/components/ConnectionIndicator.vue'
import MoneyPouch from '@/components/MoneyPouch.vue'
import PeriodClock from '@/components/PeriodClock.vue'
import type { SessionStatus } from '@/types/game'

defineEmits<{ signOut: [] }>()

const route = useRoute()
const props = withDefaults(defineProps<{
  roleLabel: string
  identity: string
  section?: string
  kicker?: string
  title?: string
  subtitle?: string
  hidePageHeading?: boolean
  navItems: { to: string; label: string; icon: string }[]
  connected: boolean
  demo?: boolean
  period: number
  elapsedMs: number
  status: SessionStatus
  money: number
  variant?: 'practical' | 'ceremonial'
}>(), { variant: 'practical' })
void route
</script>
