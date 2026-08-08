<template>
  <GameShell role-label="隊伍工作區" identity="小隊 7" section="市場行情" kicker="MARKET EXCHANGE" title="先看行情，再到現場交易。" subtitle="行情提供查詢；實際買賣由市場關主依當期價格，現場手動記錄小隊與數量。" :nav-items="navItems" :connected="!isDemo" :demo="isDemo" :period="board.session.current_period" :elapsed-ms="board.session.current_period > 0 ? 1260000 : 0" :status="board.session.status" :money="wallet" @sign-out="goLogin">
    <template #heading-actions>
      <select v-model="selectedMarket" class="market-select" aria-label="選擇市場">
        <option v-for="market in board.markets" :key="market.id" :value="market.code">{{ market.code }}・{{ market.name }}</option>
      </select>
      <button v-if="canChallenge" class="ghost-button" type="button" @click="openChallenge"><Icon name="map" size="sm" />提出據點挑戰</button>
    </template>

    <div class="notice"><Icon name="spark" size="sm" /><span><strong>{{ selectedMarketName }}</strong> 的當期行情如下。要買入或賣出，請帶隊伍到該市場，由關主確認現場條件後手動登錄。</span></div>

    <section class="section-block">
      <div class="section-block__head"><div><h2>第 {{ board.session.current_period || '—' }} 時段・市場行情</h2><p>買入、賣出價格僅供現場核對；每次交易 {{ board.config.rules.trade_quantity }} 個商品，實際成交由關主輸入</p></div><span class="status-badge is-success">查詢中</span></div>
      <table class="data-table">
        <thead><tr><th>商品</th><th>買入</th><th>賣出</th><th>持有</th><th>現場流程</th></tr></thead>
        <tbody>
          <tr v-for="rate in selectedRates" :key="rate.resource_type">
            <td><div class="team-cell"><span class="team-badge">{{ resourceFor(rate.resource_type).short_name }}</span><div><strong>{{ resourceFor(rate.resource_type).name }}</strong><span>每次 {{ board.config.rules.trade_quantity }} {{ resourceFor(rate.resource_type).unit_name }}</span></div></div></td>
            <td class="money-value">{{ rate.buy_price > 0 ? `${rate.buy_price * board.config.rules.trade_quantity} 枚` : '停止買入' }}</td><td>{{ rate.sell_price * board.config.rules.trade_quantity }} 枚</td><td>{{ inventory[rate.resource_type] || 0 }}</td>
            <td><span class="status-badge is-neutral">請關主操作</span></td>
          </tr>
        </tbody>
      </table>
      <div v-if="!selectedRates.length" class="empty-state compact-empty"><Icon name="alert" size="lg" /><strong>目前沒有可顯示的行情</strong><p>請向總召確認當期行情是否已建立。</p></div>
    </section>

    <div class="two-column">
      <section class="section-block"><div class="section-block__head"><div><h2>我的資產</h2><p>關主完成交易後，重新整理即可看到最新資產</p></div><span class="money-inline">{{ wallet }} 枚</span></div><div class="resource-list"><div v-for="resource in resources" :key="resource.key" class="resource-item"><span>{{ resource.name }}</span><strong>{{ inventory[resource.key] || 0 }}</strong></div></div></section>
      <section class="section-block"><div class="section-block__head"><div><h2>現場交易方式</h2><p>由關主代為登錄，隊伍端不直接扣款或加物資</p></div><Icon name="market" size="md" /></div><div class="process-note"><span class="process-step">1</span><p>帶著隊伍與金錢袋到市場關主處</p><span class="process-step">2</span><p>告知買／賣原料與數量，關主核對當期行情</p><span class="process-step">3</span><p>關主完成登錄後，資產才會更新</p></div></section>
    </div>

    <section v-if="actionMode === 'challenge'" class="section-block interaction-section"><div class="section-block__head"><div><h2>提出據點挑戰</h2><p>{{ selectedMarketName }}・實體挑戰由關主現場判定</p></div><Icon name="map" size="md" /></div><div class="interaction-summary"><span>挑戰難度</span><strong>難度 {{ challengeDifficulty }}</strong><em>挑戰成功後，關主會另按「套用佔領」更新市場狀態。</em></div><div class="check-grid"><label v-if="board.config.rules.guard_money_pouch" class="check-row"><input v-model="guards.money" type="checkbox" /><span>我已確認金錢袋同時出示</span></label><label v-if="board.config.rules.guard_minimum_team_present" class="check-row"><input v-model="guards.team" type="checkbox" /><span>我已確認至少半數隊員在場</span></label></div><p v-if="message" class="form-message" :class="{ 'is-error': messageType === 'error' }"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</p><div class="form-actions"><button class="ghost-button" type="button" @click="resetAction">取消</button><button class="action-button" type="button" :disabled="!guardsSatisfied || submitting" @click="submitChallenge">{{ submitting ? '送出中…' : '提出挑戰申請' }}</button></div></section>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, createMarketChallenge, getMarketBoard } from '@/lib/api'
import { cloneDefaultConfig } from '@/lib/gameConfig'
import { useSession } from '@/lib/session'
import type { MarketBoard, ProductConfig, SetupRate } from '@/types/game'

const router = useRouter()
const { state } = useSession()
const navItems = [{ to: '/user', label: '隊伍總覽', icon: 'dashboard' }, { to: '/user/market', label: '市場行情', icon: 'market' }, { to: '/user/challenges', label: '挑戰與魔王', icon: 'spark' }, { to: '/user/map', label: '市場地圖', icon: 'map' }]
const board = reactive<MarketBoard>(demoBoard())
const resources = computed(() => board.config.products)
const selectedMarket = ref('A')
const actionMode = ref<'none' | 'challenge'>('none')
const wallet = ref(218)
const inventory = reactive<Record<string, number>>({ dragon_egg: 3, time_device: 1, unicorn_blood: 5, basilisk_fang: 0 })
const guards = reactive({ money: false, team: false })
const submitting = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const isDemo = computed(() => !state.token || state.identity?.role !== 'team_facilitator')
const selectedMarketName = computed(() => board.markets.find((market) => market.code === selectedMarket.value)?.name || '市場')
const selectedRates = computed(() => board.rates.filter((rate) => rate.market_code === selectedMarket.value && rate.period === board.session.current_period))
const challengeDifficulty = computed(() => {
  const rules = board.config?.rules
  const occupied = board.markets.find((market) => market.code === selectedMarket.value)?.owner_team_id
  return occupied ? rules.challenge_occupied_difficulty : rules.challenge_default_difficulty
})
const canChallenge = computed(() => board.session.current_period >= (board.config?.rules.challenge_start_period || 3))
const guardsSatisfied = computed(() => (!board.config.rules.guard_money_pouch || guards.money) && (!board.config.rules.guard_minimum_team_present || guards.team))

onMounted(loadBoard)

async function loadBoard() {
  if (isDemo.value || !state.identity || !state.token) return
  try {
    Object.assign(board, await getMarketBoard(state.identity.session_id, state.token))
    wallet.value = board.wallet || 0
    board.inventory.forEach((item) => { inventory[item.resource_type] = item.quantity })
    selectedMarket.value = board.markets[0]?.code || 'A'
  } catch (error) { showError(error) }
}

function openChallenge() { actionMode.value = 'challenge'; clearMessage() }
function resetAction() { actionMode.value = 'none'; guards.money = false; guards.team = false; clearMessage() }
async function submitChallenge() {
  const market = board.markets.find((item) => item.code === selectedMarket.value)
  if (!market) return
  submitting.value = true
  try {
    if (isDemo.value) {
      messageType.value = 'success'
      message.value = '展示挑戰申請已送出，請在現場完成挑戰並等待關主判定。'
      return
    }
    if (!state.token) return
    await createMarketChallenge({ market_id: market.id, difficulty_level: challengeDifficulty.value, money_pouch_presented: guards.money, minimum_team_present: guards.team, idempotency_key: requestId() }, state.token)
    messageType.value = 'success'
    message.value = '挑戰申請已送到關主工作台；成功後仍由關主手動套用佔領。'
  } catch (error) { showError(error) } finally { submitting.value = false }
}
function resourceFor(key: string): ProductConfig { return resources.value.find((resource) => resource.key === key) || resources.value[0]! }
function clearMessage() { message.value = '' }
function requestId() { return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `challenge-${Date.now()}` }
function showError(error: unknown) { messageType.value = 'error'; message.value = error instanceof ApiError ? error.message : '目前無法提出挑戰。' }
function goLogin() { router.push('/login') }
function demoBoard(): MarketBoard {
  const config = cloneDefaultConfig()
  const markets = Array.from({ length: 8 }, (_, index) => { const code = String.fromCharCode(65 + index); return { id: `demo-${index}`, code, name: code, owner_team_id: index === 1 ? 'demo-team-3' : null } })
  const rates: SetupRate[] = config.products.map((resource, index) => ({ market_code: 'A', period: 2, resource_type: resource.key, buy_price: [12, 18, 8, 30][index] ?? 0, sell_price: [7, 9, 4, 2][index] ?? 0, is_public: true }))
  return { session: { current_period: 2, status: 'running' }, markets, rates, wallet: 218, inventory: [], config }
}
</script>

<style scoped>
.market-select { min-height: 40px; padding: 0 12px; color: var(--color-ink); background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: 13px; }
.money-inline { color: var(--color-primary); font-size: 18px; font-weight: 800; }
.compact-empty { padding-block: 24px; }
.process-note { display: grid; grid-template-columns: 28px 1fr; align-items: center; gap: 10px 12px; }
.process-note p { color: var(--color-muted); font-size: 12px; line-height: 1.55; }
.process-step { display: grid; place-items: center; width: 28px; height: 28px; color: var(--color-primary-strong); background: var(--color-primary-soft); border-radius: 50%; font-size: 12px; font-weight: 800; }
.interaction-section { border-color: var(--color-primary); }
.interaction-summary { display: grid; gap: 4px; margin-bottom: 14px; padding: 14px; background: var(--color-primary-soft); border-radius: var(--radius-sm); }
.interaction-summary span, .interaction-summary em { color: var(--color-muted); font-size: 11px; font-style: normal; }
.interaction-summary strong { color: var(--color-primary-strong); font-size: 16px; }
.check-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.check-row { display: flex; align-items: center; gap: 9px; min-height: 44px; padding: 0 12px; color: var(--color-ink); background: var(--color-surface); border-radius: var(--radius-sm); font-size: 12px; }
.check-row input { width: 16px; height: 16px; accent-color: var(--color-primary); }
@media (max-width: 760px) { .check-grid { grid-template-columns: 1fr; } }
</style>
