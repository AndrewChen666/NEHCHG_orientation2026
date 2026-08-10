<template>
  <GameShell role-label="市場關主" :identity="`${marketCode} 市場`" section="市場工作板" kicker="MARKET MASTER DESK" :title="`${marketCode} 市場，快速處理。`" subtitle="行情、交易、挑戰都集中在同一頁；先選隊伍，再按結果。" :nav-items="navItems" :hide-page-heading="true" :connected="!isDemo" :demo="isDemo" :period="board.session.current_period" :elapsed-ms="sessionElapsedMs" :status="board.session.status" :money="0" @sign-out="goLogin">

    <div class="field-board master-board">
      <section class="board-panel master-owner">
        <div class="master-owner__label"><span class="step-label">市場狀態</span><strong>目前佔領隊伍</strong></div>
        <label class="owner-select-field">
          <span class="sr-only">選擇目前佔領隊伍</span>
          <select v-model="selectedOwnerTeamId" aria-label="選擇目前佔領隊伍" @change="handleOwnerSelection">
            <option value="">尚未佔領</option>
            <option v-for="team in teams" :key="team.id" :value="team.id">小隊 {{ team.number }}・{{ team.name }}</option>
          </select>
        </label>
        <div class="master-owner__meta"><div class="owner-duration"><span>{{ currentOwner ? '目前已佔領' : '佔領狀態' }}</span><strong>{{ currentOwner ? formatDuration(ownerDurationMs) : '尚未佔領' }}</strong><small v-if="currentOwner">收益 {{ board.config.rules.ownership_rate_per_minute }} 枚／分鐘</small></div><span class="status-badge" :class="currentOwner ? 'is-success' : 'is-neutral'">{{ currentOwner ? '已佔領' : '尚未佔領' }}</span></div>
      </section>

      <div class="master-main">
        <section class="board-panel master-trade">
          <div class="board-panel__head"><div><span class="step-label">現場第一優先</span><h2>登錄交易</h2><p>選擇買入或售出、商品、隊伍與數量，確認後立即生效。</p></div><span class="status-badge is-neutral">{{ direction === 'buy' ? '買入' : '售出' }}</span></div>
          <div class="direction-switch" aria-label="選擇交易方向"><button class="ghost-button" :class="{ 'is-selected': direction === 'buy' }" type="button" @click="direction = 'buy'">買入</button><button class="ghost-button" :class="{ 'is-selected': direction === 'sell' }" type="button" @click="direction = 'sell'">售出</button></div>
          <div class="trade-controls">
            <label class="form-field compact-field"><span>商品</span><select v-model="selectedResource"><option v-for="rate in currentRates" :key="rate.resource_type" :value="rate.resource_type">{{ resourceFor(rate.resource_type).name }}</option></select><small v-if="selectedRate">買入 {{ selectedRate.buy_price > 0 ? `${selectedRate.buy_price} 枚` : '停止' }}・售出 {{ selectedRate.sell_price }} 枚</small></label>
            <label class="form-field compact-field quantity-field"><span>數量</span><input v-model.number="quantity" min="1" max="999" type="number" inputmode="numeric" /></label>
          </div>
          <label class="form-field compact-field trade-team-field"><span>隊伍</span><select v-model="selectedTeamId"><option v-for="team in teams" :key="team.id" :value="team.id">小隊 {{ team.number }}・{{ team.name }}（{{ team.money }} 枚）</option></select></label>
          <div class="trade-total"><span>{{ direction === 'buy' ? '小隊支出' : '小隊取得' }}</span><strong>{{ totalAmount }} 枚</strong><em>{{ selectedTeamName }}・{{ resourceFor(selectedResource).name }} × {{ quantity }}</em></div>
          <div class="check-grid compact-checks"><label v-if="board.config.rules.guard_money_pouch" class="check-row"><input v-model="guards.money" type="checkbox" /><span>金錢袋已核對</span></label><label v-if="board.config.rules.guard_minimum_team_present" class="check-row"><input v-model="guards.team" type="checkbox" /><span>半數隊員已在場</span></label></div>
          <p v-if="message" class="board-message" :class="{ 'is-error': messageType === 'error' }"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</p>
          <button class="action-button board-primary-action" :class="{ 'is-loading': submitting }" type="button" :disabled="!canSubmitTrade || submitting" :aria-busy="submitting" @click="submitTrade">{{ submitting ? '記錄中…' : '確認並記錄交易' }}<Icon name="check" size="sm" /></button>
        </section>

        <section class="board-panel master-failure">
          <div class="board-panel__head"><div><span class="step-label">現場紀錄</span><h2>新增佔領失敗紀錄</h2><p>挑戰未成功時，選隊伍並留下備註。</p></div><span class="status-badge is-neutral">只新增紀錄</span></div>
          <div class="failure-form">
            <label class="form-field compact-field"><span>隊伍</span><select v-model="failureTeamId"><option v-for="team in teams" :key="team.id" :value="team.id">小隊 {{ team.number }}・{{ team.name }}</option></select></label>
            <label class="form-field compact-field"><span>備註（選填）</span><input v-model.trim="failureNote" type="text" maxlength="500" placeholder="例如：未完成現場任務" /></label>
          </div>
          <p v-if="failureMessage" class="failure-message" :class="{ 'is-error': failureMessageType === 'error' }"><Icon :name="failureMessageType === 'error' ? 'alert' : 'check'" size="sm" />{{ failureMessage }}</p>
          <button class="action-button failure-submit" :class="{ 'is-loading': failureSubmitting }" type="button" :disabled="!failureTeamId || failureSubmitting" :aria-busy="failureSubmitting" @click="recordFailure">{{ failureSubmitting ? '記錄中…' : '新增失敗紀錄' }}<Icon name="check" size="sm" /></button>
        </section>
      </div>
    </div>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, createTransaction, getMarketBoard, recordMarketFailure, updateMarketOwnership } from '@/lib/api'
import { cloneDefaultConfig } from '@/lib/gameConfig'
import { useSession } from '@/lib/session'
import type { MarketBoard, MarketSummary, ProductConfig, ResourceKey, SetupRate } from '@/types/game'

const router = useRouter()
const { state } = useSession()
const navItems = [{ to: '/master', label: '市場工作板', icon: 'market' }]
const board = reactive<MarketBoard>(demoBoard())
const resources = computed(() => board.config.products)
const selectedTeamId = ref('demo-team-3')
const selectedOwnerTeamId = ref('demo-team-3')
const failureTeamId = ref('demo-team-4')
const failureNote = ref('')
const selectedResource = ref<ResourceKey>('dragon_egg')
const direction = ref<'buy' | 'sell'>('buy')
const quantity = ref(1)
const guards = reactive({ money: false, team: false })
const submitting = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const failureSubmitting = ref(false)
const failureMessage = ref('')
const failureMessageType = ref<'success' | 'error'>('success')
const clockNow = ref(Date.now())
const clockStartedAt = ref(Date.now())
let clockTimer: number | undefined
const isDemo = computed(() => !state.token || state.identity?.role !== 'market_master')
const marketId = computed(() => state.identity?.market_id || 'demo-1')
const fallbackMarket: MarketSummary = { id: 'demo-1', code: 'B', name: 'B' }
const currentMarket = computed<MarketSummary>(() => board.markets.find((market) => market.id === marketId.value) || board.markets[1] || board.markets[0] || fallbackMarket)
const marketCode = computed(() => currentMarket.value?.code || 'B')
const sessionElapsedMs = computed(() => {
  const base = board.session.effective_elapsed_ms ?? 0
  return board.session.status === 'running' ? base + clockNow.value - clockStartedAt.value : base
})
const currentRates = computed(() => board.rates.filter((rate) => rate.market_code === marketCode.value && rate.period === board.session.current_period))
const teams = computed(() => board.teams || [])
const selectedTeam = computed(() => teams.value.find((team) => team.id === selectedTeamId.value))
const selectedTeamName = computed(() => selectedTeam.value ? `小隊 ${selectedTeam.value.number}` : '尚未選擇小隊')
const selectedRate = computed(() => currentRates.value.find((rate) => rate.resource_type === selectedResource.value))
const unitPrice = computed(() => selectedRate.value?.[direction.value === 'buy' ? 'buy_price' : 'sell_price'] || 0)
const totalAmount = computed(() => unitPrice.value * Math.max(1, quantity.value || 0))
const guardsSatisfied = computed(() => (!board.config.rules.guard_money_pouch || guards.money) && (!board.config.rules.guard_minimum_team_present || guards.team))
const hasEnoughAssets = computed(() => {
  if (!selectedTeam.value || quantity.value < 1) return false
  return direction.value === 'buy' ? selectedTeam.value.money >= totalAmount.value : (selectedTeam.value.inventory[selectedResource.value] || 0) >= quantity.value
})
const canSubmitTrade = computed(() => Boolean(selectedTeam.value && selectedRate.value && (direction.value === 'sell' || unitPrice.value > 0) && quantity.value >= 1 && guardsSatisfied.value && hasEnoughAssets.value))
const currentOwner = computed(() => {
  const ownerId = currentMarket.value?.owner_team_id
  return teams.value.find((team) => team.id === ownerId) || (currentMarket.value?.owner_team_number ? { id: ownerId || '', number: currentMarket.value.owner_team_number, name: currentMarket.value.owner_team_name || String(currentMarket.value.owner_team_number) } : null)
})
const ownerDurationMs = computed(() => {
  const started = currentMarket.value?.owner_started_elapsed_ms
  return currentOwner.value && started != null ? Math.max(0, sessionElapsedMs.value - started) : 0
})

onMounted(async () => {
  clockTimer = window.setInterval(() => { clockNow.value = Date.now() }, 1000)
  await loadBoard()
})
onBeforeUnmount(() => { if (clockTimer) window.clearInterval(clockTimer) })

async function loadBoard() {
  if (isDemo.value || !state.identity || !state.token) return
  try { Object.assign(board, await getMarketBoard(state.identity.session_id, state.token)); clockStartedAt.value = Date.now(); selectedTeamId.value = board.teams?.[0]?.id || ''; selectedOwnerTeamId.value = currentMarket.value?.owner_team_id || ''; failureTeamId.value = board.teams?.[0]?.id || ''; selectedResource.value = currentRates.value[0]?.resource_type || board.config.products[0]?.key || 'dragon_egg'; quantity.value = board.config.rules.trade_quantity } catch (error) { showError(error) }
}
async function submitTrade() {
  const market = currentMarket.value
  if (!market || !selectedTeam.value || !canSubmitTrade.value) return
  submitting.value = true
  try {
    if (isDemo.value) {
      const team = selectedTeam.value; const items = team.inventory
      if (direction.value === 'buy') { team.money -= totalAmount.value; items[selectedResource.value] = (items[selectedResource.value] || 0) + quantity.value } else { team.money += totalAmount.value; items[selectedResource.value] = Math.max(0, (items[selectedResource.value] || 0) - quantity.value) }
      messageType.value = 'success'; message.value = `已展示記錄：${selectedTeamName.value} ${direction.value === 'buy' ? '買入' : '賣出'} ${resourceFor(selectedResource.value).name} × ${quantity.value}。`; return
    }
    if (!state.token) return
    await createTransaction({ market_id: market.id, team_id: selectedTeam.value.id, resource_type: selectedResource.value, direction: direction.value, quantity: quantity.value, money_pouch_presented: guards.money, minimum_team_present: guards.team, idempotency_key: requestId() }, state.token)
    await loadBoard(); messageType.value = 'success'; message.value = `已記錄 ${selectedTeamName.value} ${direction.value === 'buy' ? '買入' : '賣出'} ${resourceFor(selectedResource.value).name} × ${quantity.value}。`
  } catch (error) { showError(error) } finally { submitting.value = false }
}
async function handleOwnerSelection() {
  const nextTeamId = selectedOwnerTeamId.value || null
  const currentTeamId = currentMarket.value?.owner_team_id || null
  if (nextTeamId === currentTeamId) return
  try {
    if (isDemo.value) {
      const team = nextTeamId ? teams.value.find((entry) => entry.id === nextTeamId) : null
      currentMarket.value.owner_team_id = team?.id || null
      currentMarket.value.owner_team_number = team?.number || null
      currentMarket.value.owner_team_name = team?.name || null
      currentMarket.value.owner_started_elapsed_ms = team ? sessionElapsedMs.value : null
    } else {
      if (!state.token) return
      await updateMarketOwnership(currentMarket.value.id, nextTeamId, state.token)
      await loadBoard()
    }
    messageType.value = 'success'; message.value = nextTeamId ? '目前佔領隊伍已更新。' : '已清除目前佔領隊伍。'
  } catch (error) {
    selectedOwnerTeamId.value = currentTeamId || ''
    showError(error)
  }
}
async function recordFailure() {
  if (!failureTeamId.value) return
  failureSubmitting.value = true
  try {
    if (isDemo.value) {
      failureMessageType.value = 'success'; failureMessage.value = `已展示記錄小隊 ${teams.value.find((team) => team.id === failureTeamId.value)?.number || ''} 的佔領失敗。`
    } else {
      if (!state.token) return
      await recordMarketFailure({ market_id: currentMarket.value.id, team_id: failureTeamId.value, note: failureNote.value || undefined, idempotency_key: requestId('failure') }, state.token)
      failureMessageType.value = 'success'; failureMessage.value = '佔領失敗紀錄已新增。'
    }
    failureNote.value = ''
  } catch (error) {
    failureMessageType.value = 'error'; failureMessage.value = error instanceof ApiError ? error.message : '目前無法新增失敗紀錄。'
  } finally { failureSubmitting.value = false }
}
function resourceFor(key: string): ProductConfig { return resources.value.find((resource) => resource.key === key) || resources.value[0]! }
function requestId(prefix = 'master') { return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${prefix}-${Date.now()}` }
function showError(error: unknown) { messageType.value = 'error'; message.value = error instanceof ApiError ? error.message : '目前無法完成關主操作。' }
function goLogin() { router.push('/login') }
function formatDuration(milliseconds: number) { const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000)); const hours = Math.floor(totalSeconds / 3600); const minutes = Math.floor((totalSeconds % 3600) / 60); const seconds = totalSeconds % 60; return hours ? `${hours} 小時 ${String(minutes).padStart(2, '0')} 分` : `${minutes} 分 ${String(seconds).padStart(2, '0')} 秒` }
function demoBoard(): MarketBoard { const config = cloneDefaultConfig(); const markets = Array.from({ length: 8 }, (_, index) => { const code = String.fromCharCode(65 + index); return { id: `demo-${index}`, code, name: code, owner_team_id: index === 1 ? 'demo-team-3' : null, owner_team_number: index === 1 ? 3 : null, owner_team_name: index === 1 ? '3' : null, owner_started_elapsed_ms: index === 1 ? 360000 : null } }); const rates: SetupRate[] = config.products.map((resource, index) => ({ market_code: 'B', period: 2, resource_type: resource.key, buy_price: [12, 18, 8, 30][index] ?? 0, sell_price: [7, 9, 4, 2][index] ?? 0, is_public: index !== 1 })); const teams = Array.from({ length: 4 }, (_, index) => ({ id: `demo-team-${index + 3}`, number: index + 3, name: String(index + 3), money: [218, 164, 302, 96][index] ?? 0, inventory: { dragon_egg: index + 1, time_device: index, unicorn_blood: 2, basilisk_fang: 0 } })); return { session: { current_period: 2, status: 'running', effective_elapsed_ms: 1260000 }, markets, rates, wallet: null, inventory: [], teams, config } }
</script>

<style scoped>
.field-board { height: 100%; min-height: 0; }
.master-board { display: grid; grid-template-rows: auto minmax(0, 1fr); gap: 12px; }
.board-panel { min-width: 0; padding: 14px; background: var(--color-surface); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-md); }
.board-panel__head { display: flex; align-items: start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.board-panel__head h2 { margin-top: 3px; font-size: 17px; font-weight: 850; }
.board-panel__head p { margin-top: 3px; color: var(--color-muted); font-size: 11px; }
.step-label { color: var(--color-accent); font-size: 11px; font-weight: 850; }
.master-owner { display: grid; grid-template-columns: minmax(160px, .8fr) minmax(220px, 1.2fr) auto; align-items: center; gap: 12px; padding-block: 12px; }
.master-owner__label { display: grid; gap: 3px; }
.master-owner__label strong { font-size: 15px; }
.owner-select-field select { width: 100%; min-height: 40px; padding: 0 10px; color: var(--color-ink); background: var(--color-surface-raised); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-sm); font-size: 12px; }
.owner-select-field select:focus { border-color: var(--color-primary); outline: none; box-shadow: 0 0 0 3px var(--color-primary-soft); }
.master-owner__meta { display: flex; align-items: center; justify-content: flex-end; gap: 12px; color: var(--color-muted); font-size: 11px; white-space: nowrap; }
.owner-duration { display: grid; gap: 1px; text-align: right; }
.owner-duration span, .owner-duration small { color: var(--color-muted); font-size: 10px; }
.owner-duration strong { color: var(--color-ink); font-size: 14px; font-variant-numeric: tabular-nums; }
.master-main { display: grid; grid-template-columns: minmax(0, .92fr) minmax(0, 1.08fr); gap: 12px; min-height: 0; }
.master-trade, .master-failure { display: flex; flex-direction: column; min-height: 0; }
.compact-field { gap: 5px; }
.compact-field > span { font-size: 11px; }
.compact-field select, .compact-field input { min-height: 40px; }
.compact-field small { color: var(--color-muted); font-size: 10px; }
.trade-controls { display: grid; grid-template-columns: minmax(0, 1fr) 82px; gap: 8px; margin-top: 9px; }
.trade-team-field { margin-top: 9px; }
.direction-switch { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; margin-top: 9px; }
.direction-switch .ghost-button { min-height: 38px; font-size: 12px; }
.direction-switch .is-selected { color: var(--color-ink); background: var(--color-primary); border-color: var(--color-accent); }
.trade-total { display: grid; gap: 2px; margin-top: 9px; padding: 10px 12px; background: var(--color-primary-soft); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.trade-total span, .trade-total em { color: var(--color-muted); font-size: 10px; font-style: normal; }
.trade-total strong { color: var(--color-accent); font-size: 22px; font-variant-numeric: tabular-nums; }
.compact-checks { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; margin-top: 9px; }
.check-row { display: flex; align-items: center; gap: 6px; min-height: 34px; padding: 0 8px; background: var(--color-surface-quiet); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-sm); font-size: 10px; }
.check-row input { width: 14px; height: 14px; accent-color: var(--color-primary); }
.board-primary-action { width: 100%; min-height: 44px; margin-top: auto; font-size: 13px; }
.board-message { display: flex; align-items: center; gap: 6px; margin-top: 8px; color: var(--color-success); font-size: 11px; }
.board-message.is-error { color: var(--color-danger); }
.failure-form { display: grid; gap: 10px; }
.failure-message { display: flex; align-items: center; gap: 6px; margin-top: 10px; color: var(--color-success); font-size: 11px; }
.failure-message.is-error { color: var(--color-danger); }
.failure-submit { width: 100%; min-height: 44px; margin-top: auto; font-size: 13px; }
@media (max-width: 900px) { .master-main { grid-template-columns: 1fr; } .field-board { height: auto; } }
@media (max-width: 760px) { .master-owner { grid-template-columns: minmax(0, 1fr) minmax(0, 1.35fr) auto; } .master-owner__meta { min-width: 0; } .owner-duration { min-width: 0; } }
@media (max-width: 560px) {
  .master-owner { grid-template-columns: 1fr; align-items: stretch; }
  .master-owner__meta { justify-content: space-between; white-space: normal; }
  .owner-duration { text-align: left; }
  .trade-controls { grid-template-columns: 1fr; }
  .compact-checks { grid-template-columns: 1fr; }
  .board-panel__head { flex-direction: column; }
  .board-panel__head > .status-badge { align-self: flex-start; }
}
@media (max-width: 560px) {
  .direction-switch { grid-template-columns: minmax(0, 1fr); }
}
</style>
