<template>
  <div class="app-frame" :class="{ 'is-astral': isAstral, 'is-ceremonial': props.variant === 'ceremonial' }">
    <main class="main-stage">
      <header class="topbar">
        <div class="topbar-brand">
          <button class="brand-lockup" type="button" aria-label="顯示一些彩蛋" @click="revealConstellation">
            <img class="brand-mark" src="/icon.png" alt="" aria-hidden="true" />
            <span class="brand-lockup__text"><strong>活米村</strong><small>現場控制台</small></span>
          </button>
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
    <p class="spell-note" :class="{ 'is-visible': spellNote }" role="status" aria-live="polite">{{ spellNote }}</p>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { useRoute } from 'vue-router'
import ConnectionIndicator from '@/components/ConnectionIndicator.vue'
import MoneyPouch from '@/components/MoneyPouch.vue'
import PeriodClock from '@/components/PeriodClock.vue'
import type { SessionStatus } from '@/types/game'

defineEmits<{ signOut: [] }>()

const isAstral = ref(false)
const spellNote = ref('')
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
const secretKeys = ['KeyS', 'KeyT', 'KeyA', 'KeyR']
let secretKeyIndex = 0
let spellTimer: number | undefined

function revealConstellation() {
  isAstral.value = false
  window.requestAnimationFrame(() => { isAstral.value = true })
  spellNote.value = '凱文是給'
  if (spellTimer) window.clearTimeout(spellTimer)
  spellTimer = window.setTimeout(() => {
    isAstral.value = false
    spellNote.value = ''
  }, 2600)
}

function trackSecretSequence(event: KeyboardEvent) {
  const target = event.target
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) return
  secretKeyIndex = event.code === secretKeys[secretKeyIndex] ? secretKeyIndex + 1 : event.code === secretKeys[0] ? 1 : 0
  if (secretKeyIndex === secretKeys.length) {
    secretKeyIndex = 0
    revealConstellation()
  }
}

onMounted(() => {
  void route
  window.addEventListener('keydown', trackSecretSequence)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', trackSecretSequence)
  if (spellTimer) window.clearTimeout(spellTimer)
})
</script>
