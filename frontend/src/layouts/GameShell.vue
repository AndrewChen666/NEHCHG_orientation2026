<template>
  <div class="app-frame">
    <aside class="side-rail">
      <div class="brand-lockup">
        <div class="brand-mark">活</div>
        <div>
          <strong>活米村</strong>
          <span>大地遊戲控制台</span>
        </div>
      </div>

      <div class="rail-role">
        <span class="eyebrow">CURRENT ROLE</span>
        <strong>{{ roleLabel }}</strong>
        <span>{{ identity }}</span>
      </div>

      <nav class="rail-nav" aria-label="主要導覽">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="rail-link" active-class="is-active">
          <Icon :name="item.icon" size="sm" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="rail-footer">
        <ConnectionIndicator :connected="connected" :demo="demo" />
        <button class="text-button" type="button" @click="$emit('signOut')">離開工作區</button>
      </div>
    </aside>

    <main class="main-stage">
      <header class="topbar">
        <div class="breadcrumbs"><span>活米村</span><span>/</span><strong>{{ section }}</strong></div>
        <div class="topbar-actions">
          <ConnectionIndicator :connected="connected" :demo="demo" />
          <PeriodClock :period="period" :elapsed-ms="elapsedMs" :status="status" />
          <MoneyPouch :amount="money" />
        </div>
      </header>

      <div class="page-wrap">
        <section class="page-heading">
          <div>
            <span class="section-kicker">{{ kicker }}</span>
            <h1>{{ title }}</h1>
            <p>{{ subtitle }}</p>
          </div>
          <div class="heading-actions"><slot name="heading-actions" /></div>
        </section>
        <div class="page-content"><slot /></div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import Icon from '@/components/Icon.vue'
import ConnectionIndicator from '@/components/ConnectionIndicator.vue'
import MoneyPouch from '@/components/MoneyPouch.vue'
import PeriodClock from '@/components/PeriodClock.vue'
import type { SessionStatus } from '@/types/game'

defineProps<{
  roleLabel: string
  identity: string
  section: string
  kicker: string
  title: string
  subtitle: string
  navItems: { to: string; label: string; icon: string }[]
  connected: boolean
  demo?: boolean
  period: number
  elapsedMs: number
  status: SessionStatus
  money: number
}>()

defineEmits<{ signOut: [] }>()
</script>

