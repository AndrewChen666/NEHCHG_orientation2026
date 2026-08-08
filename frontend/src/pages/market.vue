<template>
  <GameShell role-label="隊伍工作區" identity="第 7 隊・鳳凰社" section="市場交易" kicker="MARKET EXCHANGE" title="先看行情，再決定出手。" subtitle="每次互動只交易一個原料；系統會替你檢查金錢、物資、上一次市場與現場確認。" :nav-items="navItems" :connected="!isDemo" :demo="isDemo" :period="board.session.current_period" :elapsed-ms="board.session.current_period > 0 ? 1260000 : 0" :status="board.session.status" :money="wallet" @sign-out="goLogin">
    <template #heading-actions><select v-model="selectedMarket" class="market-select" aria-label="選擇市場"><option v-for="market in board.markets" :key="market.id" :value="market.code">{{ market.code }}・{{ market.name }}</option></select><button v-if="board.session.current_period >= 3" class="ghost-button" type="button" @click="openChallenge"><Icon name="map" size="sm" />挑戰據點</button></template>

    <div class="notice"><Icon name="spark" size="sm" /><span><strong>{{ selectedMarketName }}</strong> 的當期行情如下。隱藏行情不會出現在隊伍端；若要交易，請帶著金錢袋並確認至少半數隊員在場。</span></div>

    <section class="section-block"><div class="section-block__head"><div><h2>第 {{ board.session.current_period || '—' }} 時段・市場行情</h2><p>每次互動交易 1 個原料，不能連續在同一市場交易</p></div><span class="status-badge is-success">可交易</span></div><table class="data-table"><thead><tr><th>原料</th><th>買入</th><th>賣出</th><th>持有</th><th>操作</th></tr></thead><tbody><tr v-for="rate in selectedRates" :key="rate.resource_type"><td><div class="team-cell"><span class="team-badge">{{ resourceFor(rate.resource_type).short }}</span><div><strong>{{ resourceFor(rate.resource_type).name }}</strong><span>單次 1 個</span></div></div></td><td class="money-value">{{ rate.buy_price }} 枚</td><td>{{ rate.sell_price }} 枚</td><td>{{ inventory[rate.resource_type] || 0 }}</td><td><div class="trade-actions"><button class="ghost-button compact" type="button" :disabled="wallet < rate.buy_price" @click="openTrade('buy', rate.resource_type)">買入</button><button class="action-button compact" type="button" :disabled="!(inventory[rate.resource_type] > 0)" @click="openTrade('sell', rate.resource_type)">賣出</button></div></td></tr></tbody></table></section>

    <div class="two-column"><section class="section-block"><div class="section-block__head"><div><h2>我的資產</h2><p>交易成功後由後端同步更新</p></div><span class="money-inline">{{ wallet }} 枚</span></div><div class="resource-list"><div v-for="resource in resources" :key="resource.key" class="resource-item"><span>{{ resource.name }}</span><strong>{{ inventory[resource.key] || 0 }}</strong></div></div></section><section class="section-block"><div class="section-block__head"><div><h2>{{ actionMode === 'challenge' ? '發起據點挑戰' : '確認互動' }}</h2><p>{{ pendingActionLabel }}</p></div><Icon :name="actionMode === 'challenge' ? 'map' : 'wallet'" size="md" /></div><div v-if="actionMode === 'none'" class="empty-state"><Icon name="spark" size="lg" /><strong>選擇一個操作</strong><p>買入、賣出或在時段 3 起發起據點挑戰，下一步會在這裡確認。</p></div><div v-else class="interaction-panel"><div class="interaction-summary"><span>{{ actionMode === 'challenge' ? '挑戰' : actionMode === 'buy' ? '買入' : '賣出' }}</span><strong>{{ actionMode === 'challenge' ? selectedMarketName : resourceFor(selectedResource).name }}</strong><em v-if="actionMode !== 'challenge'">{{ actionMode === 'buy' ? `支出 ${selectedPrice} 枚` : `獲得 ${selectedPrice} 枚` }}</em><em v-else>勝利後由關主判定佔領</em></div><label class="check-row"><input v-model="guards.money" type="checkbox" /><span>我已確認金錢袋同時出示</span></label><label class="check-row"><input v-model="guards.team" type="checkbox" /><span>我已確認至少半數隊員在場</span></label><p v-if="message" class="form-message" :class="{ 'is-error': messageType === 'error' }"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</p><div class="form-actions"><button class="ghost-button" type="button" @click="resetAction">取消</button><button class="action-button" type="button" :disabled="!guards.money || !guards.team || submitting" @click="submitAction">{{ submitting ? '送出中…' : actionMode === 'challenge' ? '送出挑戰' : '確認交易' }}</button></div></div></section></div>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, createMarketChallenge, createTransaction, getMarketBoard } from '@/lib/api'
import { useSession } from '@/lib/session'
import type { MarketBoard, SetupRate } from '@/types/game'

type ResourceKey = SetupRate['resource_type']
type ActionMode = 'none' | 'buy' | 'sell' | 'challenge'
const router = useRouter()
const { state } = useSession()
const navItems = [{ to: '/user', label: '隊伍總覽', icon: 'dashboard' }, { to: '/user/market', label: '市場交易', icon: 'market' }, { to: '/user/challenges', label: '挑戰與魔王', icon: 'spark' }, { to: '/user/map', label: '市場地圖', icon: 'map' }]
const resources: { key: ResourceKey; short: string; name: string }[] = [{ key: 'dragon_egg', short: '龍', name: '龍蛋' }, { key: 'time_device', short: '時', name: '時光器' }, { key: 'unicorn_blood', short: '血', name: '獨角獸的血' }, { key: 'basilisk_fang', short: '牙', name: '蛇妖牙齒' }]
const board = reactive<MarketBoard>(demoBoard())
const selectedMarket = ref('A')
const actionMode = ref<ActionMode>('none')
const selectedResource = ref<ResourceKey>('dragon_egg')
const wallet = ref(218)
const inventory = reactive<Record<string, number>>({ dragon_egg: 3, time_device: 1, unicorn_blood: 5, basilisk_fang: 0 })
const guards = reactive({ money: false, team: false })
const submitting = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const isDemo = computed(() => !state.token || state.identity?.role !== 'team_facilitator')
const selectedMarketName = computed(() => board.markets.find((market) => market.code === selectedMarket.value)?.name || '市場')
const selectedRates = computed(() => board.rates.filter((rate) => rate.market_code === selectedMarket.value && rate.period === board.session.current_period))
const selectedPrice = computed(() => selectedRates.value.find((rate) => rate.resource_type === selectedResource.value)?.[actionMode.value === 'buy' ? 'buy_price' : 'sell_price'] || 0)
const pendingActionLabel = computed(() => actionMode.value === 'none' ? '需要金錢袋與到場確認' : actionMode.value === 'challenge' ? '現場挑戰由關主判定' : `${selectedMarketName.value}・${resourceFor(selectedResource.value).name}`)

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

function openTrade(mode: 'buy' | 'sell', resource: ResourceKey) { actionMode.value = mode; selectedResource.value = resource; clearMessage() }
function openChallenge() { actionMode.value = 'challenge'; clearMessage() }
function resetAction() { actionMode.value = 'none'; guards.money = false; guards.team = false; clearMessage() }
async function submitAction() {
  const market = board.markets.find((item) => item.code === selectedMarket.value)
  if (!market) return
  submitting.value = true
  try {
    if (isDemo.value) {
      messageType.value = 'success'
      message.value = actionMode.value === 'challenge' ? '展示挑戰已送出，請由關主判定。' : '展示交易已完成，正式場次會由後端更新資產。'
      return
    }
    if (!state.token) return
    if (actionMode.value === 'challenge') {
      await createMarketChallenge({ market_id: market.id, difficulty_level: 3, money_pouch_presented: guards.money, minimum_team_present: guards.team, idempotency_key: requestId() }, state.token)
    } else {
      await createTransaction({ market_id: market.id, resource_type: selectedResource.value, direction: actionMode.value, money_pouch_presented: guards.money, minimum_team_present: guards.team, idempotency_key: requestId() }, state.token)
      await loadBoard()
    }
    messageType.value = 'success'
    message.value = actionMode.value === 'challenge' ? '挑戰已送到關主工作台。' : '交易成功，資產已同步。'
  } catch (error) { showError(error) } finally { submitting.value = false }
}
function resourceFor(key: string) { return resources.find((resource) => resource.key === key) || resources[0] }
function clearMessage() { message.value = '' }
function requestId() { return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `action-${Date.now()}` }
function showError(error: unknown) { messageType.value = 'error'; message.value = error instanceof ApiError ? error.message : '操作失敗，請稍後再試。' }
function goLogin() { router.push('/login') }
function demoBoard(): MarketBoard { const markets = ['北塔市場', '西廂市場', '鐘樓市場', '藥草庭', '湖畔市場', '舊書庫', '南門市場', '星象台'].map((name, index) => ({ id: `demo-${index}`, code: String.fromCharCode(65 + index), name })); const rates: SetupRate[] = resources.map((resource, index) => ({ market_code: 'A', period: 2, resource_type: resource.key, buy_price: [12, 18, 8, 30][index], sell_price: [7, 9, 4, 2][index], is_public: true })); return { session: { current_period: 2, status: 'running' }, markets, rates, wallet: 218, inventory: [] } }
</script>

<style scoped>
.market-select { min-height: 40px; padding: 0 12px; color: var(--color-ink); background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: 13px; }
.trade-actions { display: flex; justify-content: flex-end; gap: 7px; }
.compact { min-height: 34px; padding-inline: 10px; font-size: 11px; }
.money-inline { color: var(--color-primary); font-size: 18px; font-weight: 800; }
.interaction-panel { display: grid; gap: 14px; }
.interaction-summary { display: grid; gap: 4px; padding: 14px; background: var(--color-primary-soft); border-radius: var(--radius-sm); }
.interaction-summary span, .interaction-summary em { color: var(--color-muted); font-size: 11px; font-style: normal; }
.interaction-summary strong { color: var(--color-primary-strong); font-size: 16px; }
.check-row { display: flex; align-items: center; gap: 9px; color: var(--color-ink); font-size: 12px; }
.check-row input { width: 16px; height: 16px; accent-color: var(--color-primary); }
</style>
