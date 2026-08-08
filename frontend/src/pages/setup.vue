<template>
  <GameShell
    role-label="總召控制台"
    identity="活米村・開局設定"
    section="開局設定"
    kicker="SESSION SETUP"
    title="把第一個時段排好。"
    subtitle="在場次開始前確認隊伍、初始資產、市場位置與行情。開始後，這些資料會鎖定並留下稽核紀錄。"
    :nav-items="navItems"
    :connected="!isDemo"
    :demo="isDemo"
    :period="setup.session.current_period"
    :elapsed-ms="0"
    :status="setup.session.status"
    :money="0"
    @sign-out="goLogin"
  >
    <template #heading-actions>
      <button class="ghost-button" type="button" :disabled="loading" @click="loadSetup"><Icon name="clock" size="sm" />重新讀取</button>
      <button class="action-button" type="button" :disabled="saving || isDemo" @click="saveSetup"><Icon name="check" size="sm" />{{ saving ? '儲存中…' : '儲存開局設定' }}</button>
    </template>

    <div class="setup-lock">
      <Icon name="alert" size="sm" />
      <span v-if="isDemo">目前是展示資料。使用總召代碼登入後，才會讀取並寫入 Supabase 的實際場次設定。</span>
      <span v-else>場次狀態：<strong>{{ statusLabel }}</strong>。只有 draft／scheduled 可以修改開局資產；遊戲開始後所有設定會鎖定。</span>
    </div>

    <div v-if="message" class="form-message" :class="{ 'is-error': messageType === 'error' }"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</div>

    <section class="section-block">
      <div class="section-block__head"><div><h2>場次資訊</h2><p>由 bootstrap 建立；這裡先確認目前場次狀態</p></div><span class="status-badge" :class="setup.session.status === 'draft' ? 'is-neutral' : 'is-warning'">{{ statusLabel }}</span></div>
      <div class="form-grid two-up"><label class="form-field"><span>場次名稱</span><input :value="setup.session.name" type="text" readonly /></label><label class="form-field"><span>預定開始</span><input :value="formattedSchedule" type="text" readonly placeholder="手動開始" /></label></div>
    </section>

    <div class="two-column">
      <section class="section-block"><div class="section-block__head"><div><h2>12 個小隊與初始資產</h2><p>每隊金幣與四種原料會在開局前寫入錢包</p></div><span class="mini-label">{{ setup.teams.length }} / 12 隊</span></div><div class="setup-list"><div v-for="team in setup.teams" :key="team.number" class="setup-row setup-row--assets"><span class="setup-index">{{ team.number }}</span><label class="form-field"><span>隊名</span><input v-model="team.name" type="text" maxlength="40" /></label><label class="form-field"><span>金幣</span><input v-model.number="team.initial_money" type="number" min="0" /></label><label v-for="resource in resources" :key="resource.key" class="form-field"><span>{{ resource.short }}</span><input v-model.number="team.initial_inventory[resource.key]" type="number" min="0" /></label></div></div></section>

      <section class="section-block"><div class="section-block__head"><div><h2>8 個市場位置</h2><p>地圖座標使用 0–100 的相對百分比</p></div><span class="mini-label">{{ setup.markets.length }} / 8 市場</span></div><div class="setup-list"><div v-for="market in setup.markets" :key="market.code" class="setup-row setup-row--market"><span class="setup-index">{{ market.code }}</span><label class="form-field"><span>市場名稱</span><input v-model="market.name" type="text" maxlength="40" /></label><label class="form-field"><span>X</span><input v-model.number="market.map_x" type="number" min="0" max="100" /></label><label class="form-field"><span>Y</span><input v-model.number="market.map_y" type="number" min="0" max="100" /></label></div></div></section>
    </div>

    <section class="section-block"><div class="section-block__head"><div><h2>市場行情</h2><p>可切換市場與時段；公開狀態會決定隊伍端是否看到價格</p></div><div class="heading-actions"><select v-model="selectedMarket" class="setup-select" aria-label="選擇市場"><option v-for="market in setup.markets" :key="market.code" :value="market.code">{{ market.code }}・{{ market.name }}</option></select><select v-model.number="selectedPeriod" class="setup-select" aria-label="選擇時段"><option :value="1">第 1 時段</option><option :value="2">第 2 時段</option><option :value="3">第 3 時段</option><option :value="4">第 4 時段</option></select></div></div><table class="data-table setup-rate-table"><thead><tr><th>原料</th><th>買入</th><th>賣出</th><th>網站公開</th></tr></thead><tbody><tr v-for="resource in resources" :key="resource.key"><td><div class="team-cell"><span class="team-badge">{{ resource.short }}</span><div><strong>{{ resource.name }}</strong><span>每次交易 1 個</span></div></div></td><td><input v-model.number="rateFor(resource.key).buy_price" class="table-input" type="number" min="0" /></td><td><input v-model.number="rateFor(resource.key).sell_price" class="table-input" type="number" min="0" /></td><td><label class="toggle-field"><input v-model="rateFor(resource.key).is_public" type="checkbox" /><span>{{ rateFor(resource.key).is_public ? '公開' : '隱藏' }}</span></label></td></tr></tbody></table></section>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, getSetup, updateMarkets, updateRates, updateTeams } from '@/lib/api'
import { useSession } from '@/lib/session'
import type { SetupMarket, SetupRate, SetupSnapshot, SetupTeam } from '@/types/game'

type ResourceKey = 'dragon_egg' | 'time_device' | 'unicorn_blood' | 'basilisk_fang'

const router = useRouter()
const { state } = useSession()
const navItems = [{ to: '/admin', label: '總覽', icon: 'dashboard' }, { to: '/admin/setup', label: '開局設定', icon: 'spark' }, { to: '/admin/markets', label: '市場與行情', icon: 'market' }, { to: '/admin/teams', label: '隊伍資產', icon: 'team' }, { to: '/admin/map', label: '地圖與佔領', icon: 'map' }]
const resources: { key: ResourceKey; short: string; name: string }[] = [{ key: 'dragon_egg', short: '龍', name: '龍蛋' }, { key: 'time_device', short: '時', name: '時光器' }, { key: 'unicorn_blood', short: '血', name: '獨角獸的血' }, { key: 'basilisk_fang', short: '牙', name: '蛇妖牙齒' }]
const setup = reactive<SetupSnapshot>(demoSetup())
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const selectedMarket = ref('A')
const selectedPeriod = ref(1)
const isDemo = computed(() => !state.token || state.identity?.role !== 'coordinator')
const statusLabel = computed(() => ({ draft: '尚未開始', scheduled: '已排程', running: '進行中', paused: '暫停中', finished: '已結束' }[setup.session.status]))
const formattedSchedule = computed(() => setup.session.scheduled_start ? new Date(setup.session.scheduled_start).toLocaleString('zh-TW', { dateStyle: 'medium', timeStyle: 'short' }) : '手動開始')

onMounted(loadSetup)

async function loadSetup() {
  message.value = ''
  if (isDemo.value || !state.identity || !state.token) return
  loading.value = true
  try {
    Object.assign(setup, await getSetup(state.identity.session_id, state.token))
    selectedMarket.value = setup.markets[0]?.code || 'A'
    ensureRateRows()
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

async function saveSetup() {
  if (isDemo.value || !state.identity || !state.token) {
    showError(new Error('請使用總召代碼登入後再儲存設定。'))
    return
  }
  saving.value = true
  message.value = ''
  try {
    const sessionId = state.identity.session_id
    await updateTeams(sessionId, setup.teams, state.token)
    await updateMarkets(sessionId, setup.markets, state.token)
    await updateRates(sessionId, setup.rates.filter((rate) => rate.market_code === selectedMarket.value && rate.period === selectedPeriod.value), state.token)
    messageType.value = 'success'
    message.value = '開局設定已保存，下一步可由總召控制時鐘。'
  } catch (error) {
    showError(error)
  } finally {
    saving.value = false
  }
}

function ensureRateRows() {
  resources.forEach((resource) => {
    if (!setup.rates.some((rate) => rate.market_code === selectedMarket.value && rate.period === selectedPeriod.value && rate.resource_type === resource.key)) {
      setup.rates.push({ market_code: selectedMarket.value, period: selectedPeriod.value, resource_type: resource.key, buy_price: 0, sell_price: 0, is_public: true })
    }
  })
}

function rateFor(resource: ResourceKey) {
  ensureRateRows()
  return setup.rates.find((rate) => rate.market_code === selectedMarket.value && rate.period === selectedPeriod.value && rate.resource_type === resource) as SetupRate
}

function showError(error: unknown) {
  messageType.value = 'error'
  message.value = error instanceof ApiError ? error.message : error instanceof Error ? error.message : '設定讀取失敗，請稍後再試。'
}

function goLogin() { router.push('/login') }

function demoSetup(): SetupSnapshot {
  const teams: SetupTeam[] = Array.from({ length: 12 }, (_, index) => ({ id: `demo-team-${index + 1}`, number: index + 1, name: ['鳳凰社', '月桂會', '星火隊', '銀月旅團'][index % 4] + (index > 3 ? ` ${index + 1}` : ''), initial_money: 100, initial_inventory: { dragon_egg: 2, time_device: 1, unicorn_blood: 2, basilisk_fang: 0 } }))
  const markets: SetupMarket[] = ['北塔市場', '西廂市場', '鐘樓市場', '藥草庭', '湖畔市場', '舊書庫', '南門市場', '星象台'].map((name, index) => ({ id: `demo-market-${index}`, code: String.fromCharCode(65 + index), name, map_x: 15 + (index % 4) * 23, map_y: 20 + Math.floor(index / 4) * 55 }))
  return { session: { id: 'demo-session', name: '活米村・Orientation 2026', status: 'draft', scheduled_start: null, current_period: 0 }, teams, markets, rates: [] }
}
</script>

<style scoped>
.setup-row--assets { grid-template-columns: 38px minmax(125px, 1fr) 90px repeat(4, 64px); align-items: end; }
.setup-row--market { grid-template-columns: 38px minmax(0, 1fr) 68px 68px; align-items: end; }
.setup-select { min-height: 36px; padding: 0 10px; color: var(--color-ink); background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: 12px; }
.table-input { width: 86px; min-height: 36px; padding: 0 10px; color: var(--color-ink); background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.toggle-field { display: inline-flex; align-items: center; gap: 7px; color: var(--color-muted); font-size: 12px; }
.toggle-field input { accent-color: var(--color-primary); }
.setup-rate-table td:nth-child(2), .setup-rate-table td:nth-child(3) { width: 120px; }
@media (max-width: 1040px) { .setup-row--assets { grid-template-columns: 30px minmax(120px, 1fr) 80px repeat(4, 58px); } }
@media (max-width: 760px) { .setup-row--assets { grid-template-columns: 30px minmax(0, 1fr) 88px; } .setup-row--assets .form-field:nth-child(n + 4) { grid-column: 2 / span 2; } .setup-row--market { grid-template-columns: 30px minmax(0, 1fr) 64px 64px; } .section-block:has(.setup-rate-table) { overflow-x: auto; } .setup-rate-table { min-width: 560px; } }
</style>
