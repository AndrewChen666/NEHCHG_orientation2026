<template>
  <GameShell role-label="市場關主台" :identity="`${marketCode} 市場`" section="市場工作台" kicker="MARKET MASTER DESK" :title="`${marketCode} 市場，準備開市。`" subtitle="你負責現場核對、手動登錄交易，以及在挑戰成功後明確套用佔領狀態。" :nav-items="navItems" :connected="!isDemo" :demo="isDemo" :period="board.session.current_period" :elapsed-ms="board.session.current_period > 0 ? 1260000 : 0" :status="board.session.status" :money="0" @sign-out="goLogin">
    <template #heading-actions><span class="status-badge is-warning">{{ currentMarketName }}</span><button class="ghost-button" type="button"><Icon name="spark" size="sm" />呼叫總召</button></template>

    <div class="notice"><Icon name="alert" size="sm" /><span><strong>關主操作原則：</strong>小隊只提出挑戰；交易由你依當下時段行情，選擇小隊、買賣原料與數量後手動記錄。</span></div>

    <section class="section-block"><div class="section-block__head"><div><h2>第 {{ board.session.current_period || '—' }} 時段・{{ currentMarketName }} 行情</h2><p>包含本市場當期可見與隱藏行情，成交價格固定取自目前時段</p></div><span class="status-badge is-success">市場營運中</span></div><table class="data-table"><thead><tr><th>原料</th><th>買入</th><th>賣出</th><th>公開狀態</th><th>快速操作</th></tr></thead><tbody><tr v-for="rate in currentRates" :key="rate.resource_type"><td><div class="team-cell"><span class="team-badge">{{ resourceFor(rate.resource_type).short_name }}</span><div><strong>{{ resourceFor(rate.resource_type).name }}</strong><span>可輸入交易數量</span></div></div></td><td class="money-value">{{ rate.buy_price > 0 ? `${rate.buy_price} 枚` : '停止買入' }}</td><td>{{ rate.sell_price }} 枚</td><td><span class="status-badge" :class="rate.is_public ? 'is-neutral' : 'is-warning'">{{ rate.is_public ? '網站公開' : '關主可見' }}</span></td><td><div class="trade-actions"><button class="ghost-button compact" type="button" :disabled="rate.buy_price === 0" @click="openTrade('buy', rate.resource_type)">登錄買入</button><button class="action-button compact" type="button" @click="openTrade('sell', rate.resource_type)">登錄賣出</button></div></td></tr></tbody></table><div v-if="!currentRates.length" class="empty-state compact-empty"><Icon name="alert" size="lg" /><strong>目前時段尚未建立行情</strong><p>請先請總召設定本市場的當期行情。</p></div></section>

    <div class="two-column"><section class="section-block"><div class="section-block__head"><div><h2>手動登錄交易</h2><p>選擇小隊後，依現場實際成交數量記錄</p></div><Icon name="market" size="md" /></div><div class="trade-form"><label class="form-field"><span>交易小隊</span><select v-model="selectedTeamId"><option v-for="team in teams" :key="team.id" :value="team.id">小隊 {{ team.number }}・{{ team.name }}（{{ team.money }} 枚）</option></select></label><div class="form-grid two-up"><label class="form-field"><span>原料</span><select v-model="selectedResource"><option v-for="rate in currentRates" :key="rate.resource_type" :value="rate.resource_type">{{ resourceFor(rate.resource_type).name }}</option></select></label><label class="form-field"><span>數量</span><input v-model.number="quantity" min="1" max="999" type="number" inputmode="numeric" /></label></div><div class="direction-switch"><button class="ghost-button" :class="{ 'is-selected': direction === 'buy' }" type="button" @click="direction = 'buy'">小隊買入</button><button class="ghost-button" :class="{ 'is-selected': direction === 'sell' }" type="button" @click="direction = 'sell'">小隊賣出</button></div><div class="trade-total"><span>{{ direction === 'buy' ? '小隊支出' : '小隊取得' }}</span><strong>{{ totalAmount }} 枚</strong><em>{{ selectedTeamName }}・{{ resourceFor(selectedResource).name }} × {{ quantity }}</em></div><div class="check-grid"><label v-if="board.config.rules.guard_money_pouch" class="check-row"><input v-model="guards.money" type="checkbox" /><span>我已核對金錢袋</span></label><label v-if="board.config.rules.guard_minimum_team_present" class="check-row"><input v-model="guards.team" type="checkbox" /><span>我已確認至少半數隊員在場</span></label></div><p v-if="message" class="form-message" :class="{ 'is-error': messageType === 'error' }"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</p><button class="action-button" type="button" :disabled="!canSubmitTrade || submitting" @click="submitTrade">{{ submitting ? '記錄中…' : '確認並記錄這筆交易' }}<Icon name="check" size="sm" /></button></div></section>

      <section class="section-block"><div class="section-block__head"><div><h2>目前佔領</h2><p>挑戰成功後，仍需由你手動套用</p></div><span class="status-badge" :class="currentOwner ? 'is-success' : 'is-neutral'">{{ currentOwner ? `小隊 ${currentOwner.number}` : '尚未佔領' }}</span></div><div class="empty-state"><Icon name="map" size="lg" /><strong>{{ currentOwner ? `小隊 ${currentOwner.number}・${currentOwner.name}` : '目前沒有佔領隊伍' }}</strong><p>{{ currentOwner ? `目前收益 ${board.config.rules.ownership_rate_per_minute} 枚／分鐘。` : '等待成功挑戰並由關主套用佔領。' }}</p></div></section></div>

    <section class="section-block"><div class="section-block__head"><div><h2>挑戰申請與佔領處理</h2><p>先記錄實體挑戰結果；成功後再按一次套用佔領</p></div><span class="status-badge is-warning">{{ challenges.length }} 筆待處理</span></div><div v-if="challenges.length" class="event-list"><div v-for="challenge in challenges" :key="challenge.id" class="event-item"><span class="event-icon"><Icon name="team" size="sm" /></span><div><strong>小隊 {{ challenge.team_number }}・{{ challenge.team_name }}</strong><span>{{ challenge.result === 'success' ? '挑戰成功・等待套用佔領' : '等待現場判定' }}・難度 {{ challenge.difficulty_level }}</span></div><div class="decision-actions" v-if="challenge.result === 'success'"><button class="action-button compact" type="button" @click="applyOwnership(challenge.id)">套用佔領</button></div><div class="decision-actions" v-else><button class="text-button" type="button" @click="grade(challenge.id, true)">成功</button><button class="text-button is-danger" type="button" @click="grade(challenge.id, false)">失敗</button></div></div></div><div v-else class="empty-state"><Icon name="check" size="lg" /><strong>目前沒有待處理挑戰</strong><p>小隊提出挑戰後會出現在這裡。</p></div></section>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, applyChallengeOwnership, createTransaction, getMarketBoard, getPendingChallenges, gradeChallenge } from '@/lib/api'
import { cloneDefaultConfig } from '@/lib/gameConfig'
import { useSession } from '@/lib/session'
import type { MarketBoard, MarketSummary, PendingChallenge, ProductConfig, ResourceKey, SetupRate } from '@/types/game'

const router = useRouter()
const { state } = useSession()
const navItems = [{ to: '/master', label: '市場工作台', icon: 'market' }, { to: '/master/rates', label: '當期行情', icon: 'dashboard' }, { to: '/master/challenges', label: '待處理事件', icon: 'spark' }]
const board = reactive<MarketBoard>(demoBoard())
const resources = computed(() => board.config.products)
const challenges = ref<PendingChallenge[]>(demoChallenges())
const selectedTeamId = ref('demo-team-3')
const selectedResource = ref<ResourceKey>('dragon_egg')
const direction = ref<'buy' | 'sell'>('buy')
const quantity = ref(1)
const guards = reactive({ money: false, team: false })
const submitting = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const isDemo = computed(() => !state.token || state.identity?.role !== 'market_master')
const marketId = computed(() => state.identity?.market_id || 'demo-1')
const fallbackMarket: MarketSummary = { id: 'demo-1', code: 'B', name: 'B' }
const currentMarket = computed<MarketSummary>(() => board.markets.find((market) => market.id === marketId.value) || board.markets[1] || board.markets[0] || fallbackMarket)
const marketCode = computed(() => currentMarket.value?.code || 'B')
const currentMarketName = computed(() => currentMarket.value?.name || `${marketCode.value} 市場`)
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

onMounted(async () => { await loadBoard(); await loadChallenges() })

async function loadBoard() {
  if (isDemo.value || !state.identity || !state.token) return
  try {
    Object.assign(board, await getMarketBoard(state.identity.session_id, state.token))
    selectedTeamId.value = board.teams?.[0]?.id || ''
    selectedResource.value = currentRates.value[0]?.resource_type || board.config.products[0]?.key || 'dragon_egg'
    quantity.value = board.config.rules.trade_quantity
  } catch (error) { showError(error) }
}
async function loadChallenges() {
  if (isDemo.value || !state.identity?.market_id || !state.token) return
  try { challenges.value = await getPendingChallenges(state.identity.market_id, state.token) } catch (error) { showError(error) }
}
function openTrade(mode: 'buy' | 'sell', resource: ResourceKey) { direction.value = mode; selectedResource.value = resource; clearMessage() }
async function submitTrade() {
  const market = currentMarket.value
  if (!market || !selectedTeam.value || !canSubmitTrade.value) return
  submitting.value = true
  try {
    if (isDemo.value) {
      const team = selectedTeam.value
      const items = team.inventory
      if (direction.value === 'buy') { team.money -= totalAmount.value; items[selectedResource.value] = (items[selectedResource.value] || 0) + quantity.value } else { team.money += totalAmount.value; items[selectedResource.value] = Math.max(0, (items[selectedResource.value] || 0) - quantity.value) }
      messageType.value = 'success'; message.value = `已展示記錄：${selectedTeamName.value} ${direction.value === 'buy' ? '買入' : '賣出'} ${resourceFor(selectedResource.value).name} × ${quantity.value}。`; return
    }
    if (!state.token) return
    await createTransaction({ market_id: market.id, team_id: selectedTeam.value.id, resource_type: selectedResource.value, direction: direction.value, quantity: quantity.value, money_pouch_presented: guards.money, minimum_team_present: guards.team, idempotency_key: requestId() }, state.token)
    await loadBoard()
    messageType.value = 'success'; message.value = `已記錄 ${selectedTeamName.value} ${direction.value === 'buy' ? '買入' : '賣出'} ${resourceFor(selectedResource.value).name} × ${quantity.value}。`
  } catch (error) { showError(error) } finally { submitting.value = false }
}
async function grade(challengeId: string, success: boolean) {
  if (isDemo.value) { if (success) { const item = challenges.value.find((challenge) => challenge.id === challengeId); if (item) item.result = 'success' } else challenges.value = challenges.value.filter((challenge) => challenge.id !== challengeId); messageType.value = 'success'; message.value = success ? '已展示判定成功，請再按「套用佔領」。' : '已展示判定失敗，挑戰申請結束。'; return }
  if (!state.token) return
  try { await gradeChallenge(challengeId, success, undefined, state.token); if (success) { const item = challenges.value.find((challenge) => challenge.id === challengeId); if (item) item.result = 'success' } else challenges.value = challenges.value.filter((challenge) => challenge.id !== challengeId); messageType.value = 'success'; message.value = success ? '挑戰成功，請確認後套用佔領。' : '挑戰失敗，冷卻時間已建立。' } catch (error) { showError(error) }
}
async function applyOwnership(challengeId: string) {
  if (isDemo.value) { const item = challenges.value.find((challenge) => challenge.id === challengeId); const team = item && teams.value.find((entry) => entry.id === item.team_id); if (currentMarket.value && team) { currentMarket.value.owner_team_id = team.id; currentMarket.value.owner_team_number = team.number; currentMarket.value.owner_team_name = team.name } challenges.value = challenges.value.filter((challenge) => challenge.id !== challengeId); messageType.value = 'success'; message.value = '已展示套用佔領，市場現在由該隊伍持有。'; return }
  if (!state.token) return
  try { await applyChallengeOwnership(challengeId, state.token); challenges.value = challenges.value.filter((challenge) => challenge.id !== challengeId); await loadBoard(); messageType.value = 'success'; message.value = '佔領狀態已由關主手動套用。' } catch (error) { showError(error) }
}
function resourceFor(key: string): ProductConfig { return resources.value.find((resource) => resource.key === key) || resources.value[0]! }
function clearMessage() { message.value = '' }
function requestId() { return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `master-${Date.now()}` }
function showError(error: unknown) { messageType.value = 'error'; message.value = error instanceof ApiError ? error.message : '目前無法完成關主操作。' }
function goLogin() { router.push('/login') }
function demoChallenges(): PendingChallenge[] { return [{ id: 'demo-challenge-1', team_id: 'demo-team-4', team_number: 4, team_name: '4', difficulty_level: 3, result: null, created_at: new Date().toISOString() }, { id: 'demo-challenge-2', team_id: 'demo-team-3', team_number: 3, team_name: '3', difficulty_level: 4, result: 'success', ownership_applied_at: null, created_at: new Date().toISOString() }] }
function demoBoard(): MarketBoard { const config = cloneDefaultConfig(); const markets = Array.from({ length: 8 }, (_, index) => { const code = String.fromCharCode(65 + index); return { id: `demo-${index}`, code, name: code, owner_team_id: index === 1 ? 'demo-team-3' : null, owner_team_number: index === 1 ? 3 : null, owner_team_name: index === 1 ? '3' : null } }); const rates: SetupRate[] = config.products.map((resource, index) => ({ market_code: 'B', period: 2, resource_type: resource.key, buy_price: [12, 18, 8, 30][index] ?? 0, sell_price: [7, 9, 4, 2][index] ?? 0, is_public: index !== 1 })); const teams = Array.from({ length: 4 }, (_, index) => ({ id: `demo-team-${index + 3}`, number: index + 3, name: String(index + 3), money: [218, 164, 302, 96][index] ?? 0, inventory: { dragon_egg: index + 1, time_device: index, unicorn_blood: 2, basilisk_fang: 0 } })); return { session: { current_period: 2, status: 'running' }, markets, rates, wallet: null, inventory: [], teams, config } }
</script>

<style scoped>
.trade-actions { display: flex; justify-content: flex-end; gap: 7px; }
.compact { min-height: 34px; padding-inline: 10px; font-size: 11px; }
.compact-empty { padding-block: 24px; }
.trade-form { display: grid; gap: 14px; }
.direction-switch { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.direction-switch .is-selected { color: var(--color-primary-strong); background: var(--color-primary-soft); border-color: var(--color-primary); }
.trade-total { display: grid; gap: 4px; padding: 14px; background: var(--color-primary-soft); border-radius: var(--radius-sm); }
.trade-total span, .trade-total em { color: var(--color-muted); font-size: 11px; font-style: normal; }
.trade-total strong { color: var(--color-primary-strong); font-size: 22px; }
.check-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.check-row { display: flex; align-items: center; gap: 8px; min-height: 40px; padding: 0 10px; color: var(--color-ink); background: var(--color-surface); border-radius: var(--radius-sm); font-size: 11px; }
.check-row input { width: 16px; height: 16px; accent-color: var(--color-primary); }
.decision-actions { display: flex; align-items: center; gap: 10px; }
.decision-actions .is-danger { color: var(--color-danger); }
@media (max-width: 760px) { .check-grid { grid-template-columns: 1fr; } }
</style>
