<template>
  <GameShell
    role-label="總召控制台"
    identity="活米村・開局準備"
    :nav-items="navItems"
    :hide-page-heading="true"
    :connected="!isDemo"
    :demo="isDemo"
    :period="setup.session.current_period"
    :elapsed-ms="0"
    :status="setup.session.status"
    :money="0"
    @sign-out="goLogin"
  >
    <template #heading-actions>
      <button class="ghost-button" :class="{ 'is-loading': loading }" type="button" :disabled="loading" @click="loadSetup"><Icon name="clock" size="sm" />重新讀取</button>
      <button class="action-button" :class="{ 'is-loading': saving }" type="button" :disabled="saving || isDemo || isLocked" @click="saveSetup"><Icon name="check" size="sm" />{{ saving ? '儲存中…' : '儲存隊名與地圖' }}</button>
    </template>

    <section class="setup-hero" aria-labelledby="setup-title">
      <div>
        <h1 id="setup-title">60 分鐘，現場只需要確認。</h1>
        <p>遊戲規則、物資、開局金幣與行情已依規則表鎖定。這裡只保留尚未確認的隊名、顯示資訊與市場位置。</p>
      </div>
      <span class="status-badge" :class="isLocked ? 'is-warning' : 'is-success'">{{ isLocked ? '遊戲已鎖定' : '可完成準備' }}</span>
    </section>

    <p v-if="message" class="form-message" :class="{ 'is-error': messageType === 'error' }"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</p>

    <nav class="setup-tabs" aria-label="開局準備分頁">
      <button v-for="tab in tabs" :key="tab.id" class="setup-tab" :class="{ 'is-selected': activeTab === tab.id }" type="button" :aria-current="activeTab === tab.id ? 'page' : undefined" @click="activeTab = tab.id">
        <Icon :name="tab.icon" size="sm" /><span>{{ tab.label }}</span><small>{{ tab.meta }}</small>
      </button>
    </nav>

    <section v-if="activeTab === 'overview'" class="setup-panel overview-panel">
      <div class="section-block__head"><div><h2>遊戲規則總覽</h2><p>這些是場次的固定裁判條件，不會因為儲存隊名或地圖而改變。</p></div><span class="status-badge is-neutral">規則表版本</span></div>
      <dl class="rule-ledger">
        <div><dt>遊戲結構</dt><dd><strong>60 分鐘</strong><span>4 個時段，每段 15 分鐘</span></dd></div>
        <div><dt>起始資產</dt><dd><strong>15 枚</strong><span>12 隊、物資皆從 0 開始</span></dd></div>
        <div><dt>市場交易</dt><dd><strong>8 個市場</strong><span>每次 1 個原料，不可連續同市場</span></dd></div>
        <div><dt>據點佔領</dt><dd><strong>第 3 段開放</strong><span>3 枚／分鐘；失敗冷卻 3 分鐘</span></dd></div>
        <div><dt>隱藏魔王</dt><dd><strong>第 1 段開放</strong><span>I–V：1／3／5／10／20 枚</span></dd></div>
        <div><dt>黑心商人</dt><dd><strong>第 2 段開放</strong><span>每次抽卡 10 枚</span></dd></div>
      </dl>
      <div class="fixed-goods" aria-label="固定交易物資"><span v-for="product in setup.config.products" :key="product.key"><b>{{ product.short_name }}</b>{{ product.name }}・{{ product.unit_name }}</span></div>
      <div class="notice"><Icon name="alert" size="sm" /><span>所有交易、挑戰與抽卡，都必須由關主確認金錢袋與半數以上隊員在場後才可記錄。</span></div>
    </section>

    <section v-else-if="activeTab === 'teams'" class="setup-panel">
      <div class="section-block__head"><div><h2>12 支隊伍</h2><p>只設定大家在系統裡看得到的名稱與識別；每隊開局資產固定為 15 枚與 0 物資。</p></div><span class="status-badge is-neutral">{{ setup.teams.length }} / 12</span></div>
      <div class="team-grid">
        <article v-for="team in setup.teams" :key="team.number" class="team-card">
          <div class="team-card__head"><span class="team-card__number">{{ String(team.number).padStart(2, '0') }}</span><div><strong>第 {{ team.number }} 隊</strong><small>開局：15 枚・0 物資</small></div></div>
          <div class="team-fields">
            <label class="form-field"><span>隊名</span><input v-model.trim="team.name" :disabled="isLocked" maxlength="40" /></label>
            <label class="form-field"><span>英文名稱</span><input v-model.trim="team.english_name" :disabled="isLocked" maxlength="40" placeholder="TEAM 01" /></label>
            <label class="form-field"><span>圖示</span><input v-model.trim="team.icon" :disabled="isLocked" maxlength="4" /></label>
            <label class="form-field"><span>色調</span><select v-model="team.tone" :disabled="isLocked"><option v-for="tone in tones" :key="tone.value" :value="tone.value">{{ tone.label }}</option></select></label>
            <label class="form-field team-fields__wide"><span>簡短說明</span><input v-model.trim="team.description" :disabled="isLocked" maxlength="120" placeholder="例如：第 1 小隊" /></label>
          </div>
        </article>
      </div>
    </section>

    <section v-else-if="activeTab === 'markets'" class="setup-panel">
      <div class="section-block__head"><div><h2>市場位置</h2><p>市場數量與代碼 A–H 固定；可填入現場地圖要顯示的名稱與相對座標。</p></div><span class="status-badge is-neutral">8 個市場</span></div>
      <div class="market-list">
        <article v-for="market in setup.markets" :key="market.code" class="market-editor"><span class="market-editor__code">{{ market.code }}</span><label class="form-field"><span>市場名稱</span><input v-model.trim="market.name" :disabled="isLocked" maxlength="40" /></label><label class="form-field"><span>X 座標</span><input v-model.number="market.map_x" :disabled="isLocked" type="number" min="0" max="100" /></label><label class="form-field"><span>Y 座標</span><input v-model.number="market.map_y" :disabled="isLocked" type="number" min="0" max="100" /></label></article>
      </div>
    </section>

    <section v-else class="setup-panel rates-panel">
      <div class="section-block__head"><div><h2>固定市場行情</h2><p>「買」是小隊向市場買入；「賣」是小隊向市場售出。破折號代表該方向未開放。</p></div><span class="status-badge is-neutral">不可修改</span></div>
      <div class="period-picker" role="tablist" aria-label="選擇行情時段"><button v-for="period in [1, 2, 3, 4]" :key="period" type="button" :class="{ 'is-selected': selectedPeriod === period }" :aria-selected="selectedPeriod === period" role="tab" @click="selectedPeriod = period">第 {{ period }} 時段</button></div>
      <div class="rate-table-wrap"><table class="rate-table"><thead><tr><th>市場</th><th v-for="product in setup.config.products" :key="product.key"><b>{{ product.short_name }}</b><span>{{ product.name }}</span></th></tr></thead><tbody><tr v-for="market in setup.markets" :key="market.code"><th><span>{{ market.code }}</span>{{ market.name }}</th><td v-for="product in setup.config.products" :key="product.key"><div class="rate-direction"><span>買</span><strong>{{ displayRate(rateFor(market.code, product.key)?.buy_price) }}</strong></div><div class="rate-direction"><span>賣</span><strong>{{ displayRate(rateFor(market.code, product.key)?.sell_price) }}</strong></div></td></tr></tbody></table></div>
      <div class="notice"><Icon name="spark" size="sm" /><span>行情、交易方向與金額皆以這張固定規則表為準；系統會用即時交易紀錄作為裁判依據。</span></div>
    </section>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, getSetup, updateMarkets, updateTeams } from '@/lib/api'
import { cloneDefaultConfig, defaultMarketRates } from '@/lib/gameConfig'
import { useSession } from '@/lib/session'
import type { SetupSnapshot, SetupTeam } from '@/types/game'

type SetupTabId = 'overview' | 'teams' | 'markets' | 'rates'

const router = useRouter()
const route = useRoute()
const { state } = useSession()
const setup = reactive<SetupSnapshot>(demoSetup())
const activeTab = ref<SetupTabId>('overview')
const selectedPeriod = ref(1)
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const isDemo = computed(() => !state.token || state.identity?.role !== 'coordinator')
const isLocked = computed(() => ['running', 'paused', 'finished'].includes(setup.session.status))
const navItems = [{ to: '/admin', label: '總覽', icon: 'dashboard' }, { to: '/admin/activity', label: '活動流程', icon: 'clock' }, { to: '/admin/setup', label: '開局準備', icon: 'spark' }, { to: '/admin/markets', label: '市場與行情', icon: 'market' }, { to: '/admin/teams', label: '隊伍資料', icon: 'team' }, { to: '/admin/map', label: '地圖與佔領', icon: 'map' }]
const tabs = computed(() => [
  { id: 'overview' as const, label: '規則總覽', icon: 'spark', meta: '固定' },
  { id: 'teams' as const, label: '隊伍資料', icon: 'team', meta: `${setup.teams.length} 隊` },
  { id: 'markets' as const, label: '市場位置', icon: 'map', meta: 'A–H' },
  { id: 'rates' as const, label: '市場行情', icon: 'market', meta: '4 段' },
])
const tones = [{ value: 'aurora', label: '極光藍' }, { value: 'ignis', label: '焰心紅' }, { value: 'terra', label: '大地綠' }, { value: 'aqua', label: '潮汐青' }, { value: 'nova', label: '星耀紫' }, { value: 'solis', label: '日冕金' }, { value: 'ventus', label: '風行綠' }, { value: 'luna', label: '月影藍' }]

watch(() => route.path, (path) => { activeTab.value = path === '/admin/markets' ? 'rates' : path === '/admin/teams' ? 'teams' : 'overview' }, { immediate: true })
onMounted(loadSetup)

function rateFor(marketCode: string, resourceType: string) { return setup.rates.find((rate) => rate.market_code === marketCode && rate.period === selectedPeriod.value && rate.resource_type === resourceType) }
function displayRate(price?: number) { return price && price > 0 ? `${price} 枚` : '—' }

async function loadSetup() {
  message.value = ''
  if (isDemo.value || !state.identity || !state.token) return
  loading.value = true
  try { Object.assign(setup, await getSetup(state.identity.session_id, state.token)) } catch (error) { showError(error) } finally { loading.value = false }
}

async function saveSetup() {
  if (isDemo.value || !state.identity || !state.token || isLocked.value) return
  saving.value = true
  message.value = ''
  try {
    await updateTeams(state.identity.session_id, setup.teams, state.token)
    await updateMarkets(state.identity.session_id, setup.markets, state.token)
    messageType.value = 'success'
    message.value = '隊名與市場位置已儲存；固定遊戲規則與行情沒有被更動。'
  } catch (error) { showError(error) } finally { saving.value = false }
}

function showError(error: unknown) { messageType.value = 'error'; message.value = error instanceof ApiError ? error.message : '目前無法儲存設定，請重新讀取後再試。' }
function goLogin() { router.push('/login') }

function demoSetup(): SetupSnapshot {
  const config = cloneDefaultConfig()
  const teams: SetupTeam[] = Array.from({ length: 12 }, (_, index) => ({ id: `demo-team-${index + 1}`, number: index + 1, name: `第 ${index + 1} 隊`, english_name: `TEAM ${String(index + 1).padStart(2, '0')}`, icon: String(index + 1), description: '等待設定隊名', tone: tones[index % tones.length]?.value || 'aurora', initial_money: 15, initial_inventory: { dragon_egg: 0, time_device: 0, unicorn_blood: 0, basilisk_fang: 0 } }))
  const markets = Array.from({ length: 8 }, (_, index) => ({ id: `demo-market-${index}`, code: String.fromCharCode(65 + index), name: `${String.fromCharCode(65 + index)} 市場`, map_x: 15 + (index % 4) * 23, map_y: 20 + Math.floor(index / 4) * 55 }))
  return { session: { id: 'demo-session', name: '活米村・Orientation 2026', status: 'draft', scheduled_start: null, current_period: 0 }, config, teams, markets, rates: defaultMarketRates() }
}
</script>

<style scoped>
.setup-hero { display: flex; align-items: end; justify-content: space-between; gap: 24px; padding: 24px; color: var(--color-ink-inverse); background: var(--color-bg-deep); border-radius: var(--radius-md); box-shadow: var(--shadow-float); }
.setup-hero h1 { max-width: 16ch; font-family: 'Noto Serif TC', 'Source Han Serif TC', serif; font-size: clamp(26px, 4vw, 42px); font-weight: 700; line-height: 1.15; letter-spacing: -.03em; }
.setup-hero p { max-width: 62ch; margin-top: 10px; color: var(--color-muted-inverse); font-size: 13px; line-height: 1.7; }
.setup-tabs { display: flex; gap: 8px; overflow-x: auto; margin-top: 18px; padding-bottom: 2px; }
.setup-tab { display: inline-flex; min-height: 44px; align-items: center; gap: 7px; padding: 0 12px; color: var(--color-muted); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: 12px; font-weight: 800; white-space: nowrap; }
.setup-tab small { color: inherit; font-size: 10px; font-variant-numeric: tabular-nums; opacity: .72; }.setup-tab.is-selected { color: white; background: var(--color-primary); border-color: var(--color-primary); }.setup-tab:focus-visible { outline: 3px solid var(--color-accent); outline-offset: 2px; }
.setup-panel { margin-top: 16px; padding: 20px; background: var(--color-surface); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-md); }.section-block__head { display: flex; align-items: start; justify-content: space-between; gap: 16px; margin-bottom: 18px; }.section-block__head h2 { font-size: 19px; }.section-block__head p { max-width: 68ch; margin-top: 4px; color: var(--color-muted); font-size: 12px; line-height: 1.6; }
.rule-ledger { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px; background: var(--color-border); border: 1px solid var(--color-border); }.rule-ledger > div { display: grid; gap: 5px; min-height: 118px; padding: 16px; background: var(--color-surface-raised); }.rule-ledger dt { color: var(--color-muted); font-size: 11px; }.rule-ledger dd { display: grid; gap: 4px; margin: 0; }.rule-ledger strong { color: var(--color-primary-strong); font-size: 18px; }.rule-ledger span { color: var(--color-muted); font-size: 11px; line-height: 1.55; }
.fixed-goods { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }.fixed-goods span { display: inline-flex; align-items: center; gap: 7px; min-height: 34px; padding: 0 10px; color: var(--color-ink); background: var(--color-surface-quiet); border-radius: var(--radius-sm); font-size: 12px; }.fixed-goods b { display: grid; width: 20px; height: 20px; place-items: center; color: white; background: var(--color-primary); border-radius: 50%; font-size: 10px; }.notice { display: flex; align-items: center; gap: 8px; margin-top: 16px; padding: 11px 12px; color: var(--color-primary-strong); background: var(--color-info-soft); border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: 12px; line-height: 1.55; }.notice .icon { flex: 0 0 auto; }
.team-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }.team-card { padding: 14px; background: var(--color-surface-raised); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-sm); }.team-card__head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }.team-card__number, .market-editor__code { display: grid; width: 34px; height: 34px; flex: 0 0 auto; place-items: center; color: white; background: var(--color-primary); border-radius: 50%; font-size: 11px; font-weight: 850; font-variant-numeric: tabular-nums; }.team-card__head strong, .team-card__head small { display: block; }.team-card__head strong { font-size: 13px; }.team-card__head small { margin-top: 2px; color: var(--color-muted); font-size: 10px; }.team-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }.team-fields__wide { grid-column: 1 / -1; }.form-field { display: grid; gap: 5px; min-width: 0; }.form-field > span { color: var(--color-muted); font-size: 10px; font-weight: 800; }.form-field input, .form-field select { width: 100%; min-width: 0; height: 36px; padding: 0 9px; color: var(--color-ink); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; font: inherit; font-size: 12px; }.form-field input:focus, .form-field select:focus { border-color: var(--color-primary); outline: 2px solid var(--color-primary-soft); outline-offset: 1px; }.form-field input:disabled, .form-field select:disabled { color: var(--color-muted); background: var(--color-surface-quiet); cursor: not-allowed; }
.market-list { display: grid; gap: 8px; }.market-editor { display: grid; grid-template-columns: 40px minmax(0, 1fr) 110px 110px; gap: 12px; align-items: end; padding: 12px; background: var(--color-surface-raised); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-sm); }.market-editor__code { border-radius: var(--radius-sm); }
.period-picker { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }.period-picker button { min-height: 40px; padding: 0 13px; color: var(--color-primary-strong); background: var(--color-primary-soft); border: 1px solid transparent; border-radius: var(--radius-sm); font-size: 12px; font-weight: 850; }.period-picker button.is-selected { color: white; background: var(--color-primary); border-color: var(--color-primary); }.rate-table-wrap { overflow: auto; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }.rate-table { width: 100%; min-width: 760px; border-collapse: collapse; }.rate-table th, .rate-table td { padding: 10px 12px; border-right: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border); text-align: left; }.rate-table tr:last-child th, .rate-table tr:last-child td { border-bottom: 0; }.rate-table th:last-child, .rate-table td:last-child { border-right: 0; }.rate-table thead th { color: var(--color-primary-strong); background: var(--color-primary-soft); font-size: 11px; }.rate-table thead b, .rate-table thead span { display: block; }.rate-table thead span { margin-top: 3px; color: var(--color-muted); font-size: 10px; font-weight: 500; }.rate-table tbody th { min-width: 130px; font-size: 12px; }.rate-table tbody th span { display: inline-grid; width: 22px; height: 22px; place-items: center; margin-right: 7px; color: white; background: var(--color-primary); border-radius: 50%; font-size: 10px; }.rate-direction { display: flex; justify-content: space-between; gap: 10px; color: var(--color-muted); font-size: 10px; }.rate-direction + .rate-direction { margin-top: 6px; }.rate-direction strong { color: var(--color-ink); font-size: 12px; font-variant-numeric: tabular-nums; }.rate-direction:last-child strong { color: var(--color-success); }
@media (max-width: 900px) { .team-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.rule-ledger { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 620px) { .setup-hero { align-items: start; flex-direction: column; padding: 19px; }.setup-hero h1 { font-size: 29px; }.setup-panel { margin-inline: -2px; padding: 15px; }.section-block__head { align-items: start; flex-direction: column; }.rule-ledger { grid-template-columns: 1fr; }.rule-ledger > div { min-height: 0; }.team-grid { grid-template-columns: 1fr; }.market-editor { grid-template-columns: 36px minmax(0, 1fr) 76px 76px; gap: 8px; }.market-editor .form-field > span { font-size: 9px; }.market-editor .form-field input { padding-inline: 6px; }.rate-table-wrap { width: calc(100% + 30px); margin-inline: -15px; border-right: 0; border-left: 0; border-radius: 0; }.notice { align-items: start; } }
</style>
