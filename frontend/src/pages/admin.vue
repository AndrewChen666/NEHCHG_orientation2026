<template>
  <GameShell
    role-label="總召控制台"
    identity="活米村・主控席"
    :nav-items="navItems"
    :hide-page-heading="true"
    :connected="!isDemo"
    :demo="isDemo"
    :period="activePeriod"
    :elapsed-ms="displayedElapsed"
    :status="snapshot.session.status"
    :money="0"
    @sign-out="goLogin"
  >
    <div class="admin-board">
      <header class="admin-heading">
        <div><h1>總召工作台</h1><p>先處理需要決定的事，再查看全場狀態。所有資料會即時同步。</p></div>
        <div class="admin-heading__actions"><button class="ghost-button" :class="{ 'is-loading': loading }" type="button" :disabled="loading" @click="loadDashboard"><Icon name="clock" size="sm" />重新讀取</button><RouterLink class="action-button" to="/admin/setup"><Icon name="spark" size="sm" />開局準備</RouterLink></div>
      </header>

      <section class="admin-now" aria-label="現場狀態">
        <div class="admin-now__period"><span>目前時段</span><div><strong>{{ activePeriod ? `第 ${activePeriod} 段` : '尚未進行' }}</strong><em :class="`is-${snapshot.session.status}`"><i />{{ statusLabel }}</em></div><small>{{ periodTiming }}</small></div>
        <dl class="admin-now__facts"><div><dt>場上總金幣</dt><dd>{{ totalMoney.toLocaleString() }}</dd><small>開局共 {{ openingMoney.toLocaleString() }} 枚</small></div><div><dt>已佔領據點</dt><dd>{{ ownedMarketCount }} / {{ snapshot.markets.length }}</dd><small>{{ snapshot.markets.length - ownedMarketCount }} 個市場仍開放</small></div></dl>
        <div class="admin-now__attention"><div><span>時段安全閥</span><strong>{{ snapshot.session.manual_period_override ? '手動鎖定中' : '自動換段中' }}</strong></div><p>{{ snapshot.session.manual_period_override ? `全場目前固定在第 ${snapshot.session.manual_period_override} 段；累積時間仍會保留。` : '每 15 分鐘自動換段。遇到意外可先暫停，再指定正確時段。' }}</p><span v-if="clockMessage" class="clock-message" :class="{ 'is-error': clockMessageType === 'error' }" aria-live="polite">{{ clockMessage }}</span></div>
      </section>

      <section class="clock-control section-block" aria-labelledby="clock-control-title">
        <div class="section-block__head"><div><span class="step-label">總召專用</span><h2 id="clock-control-title">遊戲時鐘與時段控制</h2><p>暫停會凍結全場規則與收入；恢復後會沿用原本累積時間。手動時段只覆蓋顯示與規則判定，不會重設計時。</p></div><span class="status-badge" :class="snapshot.session.manual_period_override ? 'is-warning' : 'is-success'">{{ snapshot.session.manual_period_override ? '人工覆寫' : '15 分鐘自動' }}</span></div>
        <div class="clock-control__body">
          <div class="clock-control__actions"><button v-if="snapshot.session.status === 'draft' || snapshot.session.status === 'scheduled'" class="action-button" type="button" :disabled="clockBusy" @click="performClockAction('start')"><Icon name="clock" size="sm" />開始 60 分鐘遊戲</button><button v-else-if="snapshot.session.status === 'running'" class="ghost-button is-warning" type="button" :disabled="clockBusy" @click="performClockAction('pause')"><Icon name="alert" size="sm" />暫停全場</button><button v-else-if="snapshot.session.status === 'paused'" class="action-button" type="button" :disabled="clockBusy" @click="performClockAction('resume')"><Icon name="clock" size="sm" />恢復計時</button><button v-if="snapshot.session.status === 'running' || snapshot.session.status === 'paused'" class="ghost-button is-danger" type="button" :disabled="clockBusy" @click="performClockAction('finish')">結束並結算</button></div>
          <div class="period-switch" :class="{ 'is-disabled': !periodControlAvailable }"><div><span>指定目前時段</span><small>先選擇，再按套用，避免誤觸。</small></div><div class="period-switch__choices" role="radiogroup" aria-label="指定遊戲時段"><button v-for="period in [1, 2, 3, 4]" :key="period" type="button" :class="{ 'is-selected': requestedPeriod === period }" :aria-checked="requestedPeriod === period" role="radio" :disabled="!periodControlAvailable || clockBusy" @click="requestedPeriod = period">第 {{ period }} 段</button></div><div class="period-switch__apply"><button class="action-button" type="button" :disabled="!periodControlAvailable || !requestedPeriod || requestedPeriod === snapshot.session.manual_period_override || clockBusy" @click="applyRequestedPeriod">{{ requestedPeriod ? `切換為第 ${requestedPeriod} 段` : '先選擇時段' }}</button><button class="ghost-button" type="button" :disabled="!periodControlAvailable || !snapshot.session.manual_period_override || clockBusy" @click="clearPeriodOverride">恢復自動換段</button></div></div>
        </div>
      </section>

      <div class="admin-dashboard">
        <section class="section-block leaderboard-panel">
          <div class="section-block__head"><div><h2>隊伍金幣排行</h2><p>依目前金錢袋排序</p></div><RouterLink class="text-button" to="/admin/teams">查看隊伍資產 →</RouterLink></div>
          <div class="data-table-scroll">
            <table class="data-table"><thead><tr><th>隊伍</th><th>金幣</th><th>資產趨勢</th><th>狀態</th></tr></thead><tbody>
              <tr v-for="team in rankedTeams" :key="team.number"><td data-label="隊伍"><div class="team-cell"><span class="team-badge">{{ team.number }}</span><div><strong>{{ team.name }}</strong><span>{{ team.note }}</span></div></div></td><td data-label="金幣" class="money-value">{{ team.money.toLocaleString() }}</td><td data-label="資產趨勢"><div class="rank-bar"><span :style="{ width: `${team.ratio}%` }" /></div></td><td data-label="狀態"><span class="status-badge" :class="team.statusClass">{{ team.status }}</span></td></tr>
            </tbody></table>
          </div>
        </section>
        <section class="section-block events-panel"><div class="section-block__head"><div><h2>剛發生的事件</h2><p>所有操作都會留下紀錄</p></div><span class="status-badge is-success">即時同步</span></div><div class="event-list">
          <div v-for="event in events" :key="event.title" class="event-item" :class="`is-${event.tone}`"><span class="event-icon"><Icon :name="event.icon" size="sm" /></span><div><strong>{{ event.title }}</strong><span>{{ event.detail }}</span></div><span class="event-time">{{ event.time }}</span></div>
        </div></section>
      </div>

      <div class="admin-operations">
        <section class="section-block"><div class="section-block__head"><div><h2>市場佔領</h2><p>{{ activePeriod >= 3 ? '據點挑戰已開放' : '第 3 段起開放據點挑戰' }}</p></div><RouterLink class="text-button" to="/admin/map">查看地圖 →</RouterLink></div><div class="market-list"><div v-for="market in displayMarkets" :key="market.code" class="market-row"><div class="market-row__name"><span class="market-code">{{ market.code }}</span><div><strong>{{ market.name }}</strong><span>{{ market.owner }}</span></div></div><span class="status-badge" :class="market.owner === '開放中' ? 'is-neutral' : 'is-success'">{{ market.owner === '開放中' ? '待佔領' : '已佔領' }}</span></div></div></section>
        <section class="section-block"><div class="section-block__head"><div><h2>角色分工</h2><p>總召掌握流程；現場判定留在角色工作台。</p></div><span class="status-badge is-neutral">權限分離</span></div><div class="role-note"><Icon name="spark" size="sm" /><div><strong>隱藏魔王事件</strong><span>題庫、現場挑戰、成功發獎與失敗紀錄都由魔王工作台完成。</span></div></div></section>
        <section class="section-block"><div class="section-block__head"><div><h2>常用設定</h2><p>不必在全局頁面尋找功能。</p></div></div><div class="quick-links"><RouterLink v-for="item in quickActions" :key="item.label" :to="item.to"><Icon :name="item.icon" size="sm" /><span><strong>{{ item.label }}</strong><small>{{ item.detail }}</small></span><Icon name="arrow" size="sm" /></RouterLink></div></section>
      </div>
    </div>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, getSnapshot, updateClock, updatePeriodOverride } from '@/lib/api'
import { useSession } from '@/lib/session'
import type { GameSnapshot, SessionStatus } from '@/types/game'

const router = useRouter()
const { state } = useSession()
const snapshot = reactive<GameSnapshot>(demoSnapshot())
const loading = ref(false)
const clockBusy = ref(false)
const clockMessage = ref('')
const clockMessageType = ref<'success' | 'error'>('success')
const requestedPeriod = ref<number | null>(null)
const observedAt = ref(Date.now())
const now = ref(Date.now())
let clockTicker: ReturnType<typeof setInterval> | undefined
const isDemo = computed(() => !state.token || state.identity?.role !== 'coordinator')
const navItems = [{ to: '/admin', label: '總覽', icon: 'dashboard' }, { to: '/admin/activity', label: '活動流程', icon: 'clock' }, { to: '/admin/setup', label: '開局準備', icon: 'spark' }, { to: '/admin/markets', label: '市場與行情', icon: 'market' }, { to: '/admin/teams', label: '隊伍資料', icon: 'team' }, { to: '/admin/map', label: '地圖與佔領', icon: 'map' }]
const quickActions = [{ icon: 'clock', label: '活動流程', detail: '查看固定 60 分鐘規則', to: '/admin/activity' }, { icon: 'spark', label: '開局準備', detail: '隊名、地圖與固定規則', to: '/admin/setup' }, { icon: 'market', label: '查看行情', detail: '依時段查看固定市場價格', to: '/admin/markets' }]
const displayedElapsed = computed(() => snapshot.session.status === 'running'
  ? snapshot.session.effective_elapsed_ms + Math.max(0, now.value - observedAt.value)
  : snapshot.session.effective_elapsed_ms)
const activePeriod = computed(() => {
  if (snapshot.session.manual_period_override) return snapshot.session.manual_period_override
  if (snapshot.session.status !== 'running' && snapshot.session.status !== 'paused') return snapshot.session.current_period
  const automatic = Math.floor(displayedElapsed.value / (15 * 60_000)) + 1
  return automatic <= 4 ? automatic : 0
})
const statusLabel = computed(() => ({ draft: '尚未開始', scheduled: '等待開始', running: '進行中', paused: '已暫停', finished: '已結束' }[snapshot.session.status]))
const periodControlAvailable = computed(() => snapshot.session.status === 'running' || snapshot.session.status === 'paused')
const totalMoney = computed(() => snapshot.teams.reduce((total, team) => total + team.money, 0))
const openingMoney = computed(() => snapshot.teams.length * 15)
const ownedMarketCount = computed(() => snapshot.markets.filter((market) => Boolean(market.owner_team_id)).length)
const rankedTeams = computed(() => {
  const owners = new Map<string, number>()
  snapshot.markets.forEach((market) => { if (market.owner_team_id) owners.set(market.owner_team_id, (owners.get(market.owner_team_id) || 0) + 1) })
  const richest = Math.max(1, ...snapshot.teams.map((team) => team.money))
  return [...snapshot.teams].sort((left, right) => right.money - left.money || left.number - right.number).map((team, index) => {
    const holdings = owners.get(team.id) || 0
    return {
      ...team,
      ratio: Math.max(4, Math.round(team.money / richest * 100)),
      note: holdings ? `持有 ${holdings} 個據點` : '即時錢包餘額',
      status: index === 0 ? '領先中' : holdings ? '持有據點' : '進行中',
      statusClass: index === 0 || holdings ? 'is-success' : 'is-neutral',
    }
  })
})
const displayMarkets = computed(() => {
  const names = new Map(snapshot.teams.map((team) => [team.id, `第 ${team.number} 隊・${team.name}`]))
  return snapshot.markets.map((market) => ({ ...market, owner: market.owner_team_id ? names.get(market.owner_team_id) || '已佔領' : '開放中' }))
})
const events = computed(() => [
  snapshot.session.manual_period_override
    ? { icon: 'alert', title: `時段固定在第 ${snapshot.session.manual_period_override} 段`, detail: '總召可在安全閥中恢復自動換段。', time: '目前', tone: 'alert' }
    : { icon: 'clock', title: '15 分鐘自動換段已啟用', detail: '總召可隨時暫停或手動指定時段。', time: '目前', tone: 'trade' },
  { icon: 'market', title: `${ownedMarketCount.value} 個市場已有隊伍佔領`, detail: '收入會按完整分鐘入帳；結束時依規則處理剩餘秒數。', time: '即時', tone: 'capture' },
  { icon: 'spark', title: '全場狀態已同步', detail: `伺服器事件序號 ${snapshot.last_event_sequence}。`, time: '剛剛', tone: 'trade' },
])
const periodTiming = computed(() => {
  if (snapshot.session.manual_period_override) return `手動固定中・累積 ${formatElapsed(displayedElapsed.value)}`
  if (snapshot.session.status === 'paused') return `計時已暫停・累積 ${formatElapsed(displayedElapsed.value)}`
  if (snapshot.session.status !== 'running') return snapshot.session.status === 'finished' ? `遊戲結束・總計 ${formatElapsed(displayedElapsed.value)}` : '開始後將每 15 分鐘自動切換'
  if (!activePeriod.value) return '60 分鐘已到，請結束並結算'
  const remaining = 15 * 60_000 - (displayedElapsed.value % (15 * 60_000))
  return activePeriod.value === 4 ? `距離活動結束 ${formatElapsed(remaining)}` : `距離下一段 ${formatElapsed(remaining)}`
})

onMounted(() => {
  loadDashboard()
  clockTicker = setInterval(() => { now.value = Date.now() }, 1_000)
})
onUnmounted(() => { if (clockTicker) clearInterval(clockTicker) })

async function loadDashboard() {
  clockMessage.value = ''
  if (isDemo.value || !state.identity || !state.token) return
  loading.value = true
  try {
    applySnapshot(await getSnapshot(state.identity.session_id, state.token))
  } catch (error) {
    showError(error, '目前無法讀取總召控制台。')
  } finally {
    loading.value = false
  }
}

async function performClockAction(action: 'start' | 'pause' | 'resume' | 'finish') {
  if (action === 'finish' && typeof window !== 'undefined' && !window.confirm('確定要結束遊戲並結算所有據點收入嗎？此操作無法恢復。')) return
  clockBusy.value = true
  clockMessage.value = ''
  try {
    if (isDemo.value) {
      const status: SessionStatus = action === 'start' || action === 'resume' ? 'running' : action === 'pause' ? 'paused' : 'finished'
      snapshot.session.status = status
      if (action === 'start' && !snapshot.session.current_period) snapshot.session.current_period = 1
      observedAt.value = Date.now()
    } else if (state.identity && state.token) {
      const result = await updateClock(state.identity.session_id, action, state.token)
      applySession(result.session)
    }
    clockMessageType.value = 'success'
    clockMessage.value = ({ start: '60 分鐘遊戲已開始，現在會每 15 分鐘自動換段。', pause: '全場已暫停；計時、時段與據點收入都已凍結。', resume: '已恢復計時，會接續原本累積時間。', finish: '遊戲已結束，所有據點收入已完成結算。' }[action])
  } catch (error) {
    showError(error, '無法更新遊戲時鐘。')
  } finally {
    clockBusy.value = false
  }
}

async function applyRequestedPeriod() {
  if (!requestedPeriod.value) return
  await setPeriodOverride(requestedPeriod.value)
}

async function clearPeriodOverride() {
  await setPeriodOverride(null)
}

async function setPeriodOverride(period: number | null) {
  if (!periodControlAvailable.value) return
  clockBusy.value = true
  clockMessage.value = ''
  try {
    if (isDemo.value) {
      snapshot.session.manual_period_override = period
      snapshot.session.current_period = period || Math.floor(displayedElapsed.value / (15 * 60_000)) + 1
      observedAt.value = Date.now()
    } else if (state.identity && state.token) {
      const result = await updatePeriodOverride(state.identity.session_id, period, state.token)
      applySession(result.session)
    }
    requestedPeriod.value = period
    clockMessageType.value = 'success'
    clockMessage.value = period ? `已固定為第 ${period} 段；需要時可按「恢復自動換段」。` : '已解除人工覆寫，現在會依累積時間每 15 分鐘自動換段。'
  } catch (error) {
    showError(error, '無法更新目前時段。')
  } finally {
    clockBusy.value = false
  }
}

function applySnapshot(next: GameSnapshot) {
  Object.assign(snapshot, next)
  applySession(next.session)
}

function applySession(session: GameSnapshot['session']) {
  Object.assign(snapshot.session, session)
  requestedPeriod.value = session.manual_period_override || null
  observedAt.value = Date.now()
  now.value = observedAt.value
}

function formatElapsed(milliseconds: number) {
  const totalSeconds = Math.max(0, Math.ceil(milliseconds / 1_000))
  return `${String(Math.floor(totalSeconds / 60)).padStart(2, '0')}:${String(totalSeconds % 60).padStart(2, '0')}`
}

function showError(error: unknown, fallback: string) {
  clockMessageType.value = 'error'
  clockMessage.value = error instanceof ApiError ? error.message : fallback
}

const goLogin = () => router.push('/login')

function demoSnapshot(): GameSnapshot {
  const demoMoney = [17, 6, 13, 4, 9, 2, 18, 11, 7, 5, 14, 3]
  const teams = Array.from({ length: 12 }, (_, index) => ({ id: `demo-team-${index + 1}`, number: index + 1, name: `第 ${index + 1} 隊`, money: 15 + (demoMoney[index] || 0) }))
  return {
    session: { id: 'demo-session', name: '活米村・Orientation 2026', status: 'running', scheduled_start: null, started_at: null, current_period: 2, effective_elapsed_ms: 1_260_000 },
    teams,
    markets: Array.from({ length: 8 }, (_, index) => ({ id: `demo-market-${index + 1}`, code: String.fromCharCode(65 + index), name: `${String.fromCharCode(65 + index)} 市場`, owner_team_id: index === 0 ? 'demo-team-7' : index === 1 ? 'demo-team-3' : null })),
    last_event_sequence: 0,
  }
}

</script>

<style scoped>
.admin-board { display: grid; gap: 14px; }
.admin-heading { display: flex; align-items: end; justify-content: space-between; gap: 20px; padding: 2px 2px 4px; }
.admin-heading h1 { font-size: 26px; letter-spacing: -.025em; }
.admin-heading p { max-width: 56ch; margin-top: 5px; color: var(--color-muted); font-size: 13px; line-height: 1.55; }
.admin-heading__actions { display: flex; flex-wrap: wrap; gap: 8px; }
.clock-control { padding: 18px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
.clock-control .section-block__head { display: flex; align-items: start; justify-content: space-between; gap: 16px; }
.clock-control .section-block__head h2 { margin-top: 3px; font-size: 18px; }
.clock-control .section-block__head p { max-width: 70ch; margin-top: 4px; color: var(--color-muted); font-size: 12px; line-height: 1.55; }
.step-label { color: var(--color-accent); font-size: 11px; font-weight: 850; }
.clock-control__body { display: grid; grid-template-columns: minmax(180px, .55fr) minmax(0, 1.45fr); gap: 14px; padding-top: 14px; border-top: 1px solid var(--color-border-subtle); }
.clock-control__actions { display: grid; align-content: start; grid-template-columns: 1fr; gap: 8px; }
.clock-control__actions button { justify-content: center; min-height: 42px; }
.period-switch { display: grid; grid-template-columns: minmax(150px, .8fr) minmax(220px, 1.2fr) auto; align-items: center; gap: 12px; padding: 12px; background: var(--color-surface-quiet); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-sm); }
.period-switch > div:first-child { display: grid; gap: 3px; }.period-switch span { font-size: 12px; font-weight: 850; }.period-switch small { color: var(--color-muted); font-size: 10px; line-height: 1.4; }
.period-switch__choices { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 5px; }.period-switch__choices button { min-height: 36px; color: var(--color-primary-strong); background: var(--color-primary-soft); border: 1px solid transparent; border-radius: 5px; font-size: 11px; font-weight: 850; }.period-switch__choices button.is-selected { color: white; background: var(--color-primary); }.period-switch__choices button:disabled { opacity: .45; cursor: not-allowed; }
.period-switch__apply { display: grid; gap: 6px; }.period-switch__apply button { min-height: 36px; white-space: nowrap; font-size: 11px; }.period-switch.is-disabled { opacity: .6; }
.clock-message { display: block; margin-top: 8px; color: var(--color-success); font-size: 11px; font-weight: 750; line-height: 1.45; }.clock-message.is-error { color: var(--color-danger); }
.admin-now { display: grid; grid-template-columns: minmax(220px, .8fr) minmax(310px, 1.15fr) minmax(230px, .75fr); overflow: hidden; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
.admin-now > * { min-width: 0; padding: 17px 18px; }
.admin-now > * + * { border-left: 1px solid var(--color-border); }
.admin-now span, .admin-now dt { color: var(--color-muted); font-size: 11px; font-weight: 800; }
.admin-now__period > div { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-top: 7px; }
.admin-now__period strong { font-size: 27px; letter-spacing: -.03em; }
.admin-now__period em { display: inline-flex; align-items: center; gap: 6px; color: var(--color-success); font-size: 12px; font-style: normal; font-weight: 800; white-space: nowrap; }
.admin-now__period em.is-paused, .admin-now__period em.is-finished { color: var(--color-warning); }.admin-now__period em.is-draft, .admin-now__period em.is-scheduled { color: var(--color-muted); }
.admin-now__period i { width: 7px; height: 7px; background: currentColor; border-radius: 50%; }
.admin-now small { display: block; margin-top: 5px; color: var(--color-muted); font-size: 11px; }
.admin-now__facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 0; }
.admin-now__facts > div + div { padding-left: 18px; border-left: 1px solid var(--color-border-subtle); }
.admin-now__facts dd { margin: 7px 0 0; color: var(--color-ink); font-size: 22px; font-weight: 850; font-variant-numeric: tabular-nums; letter-spacing: -.02em; }
.admin-now__facts small { color: var(--color-success); }
.admin-now__attention { background: var(--color-warning-soft); }
.admin-now__attention > div { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.admin-now__attention strong { color: var(--color-warning); font-size: 24px; letter-spacing: -.02em; }
.admin-now__attention p { margin-top: 6px; color: var(--color-ink); font-size: 12px; line-height: 1.45; }
.admin-now__attention a { display: inline-block; margin-top: 8px; color: var(--color-primary-strong); font-size: 12px; font-weight: 800; }
.admin-dashboard { display: grid; grid-template-columns: minmax(0, 1.28fr) minmax(300px, .72fr); gap: 14px; }
.admin-operations { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.role-note { display: flex; gap: 10px; color: var(--color-primary); }
.role-note > div { display: grid; gap: 3px; }
.role-note strong { color: var(--color-ink); font-size: 13px; }
.role-note span { color: var(--color-muted); font-size: 12px; line-height: 1.55; }
.quick-links { display: grid; gap: 2px; }
.quick-links a { display: grid; grid-template-columns: 20px minmax(0, 1fr) 16px; align-items: center; gap: 9px; padding: 9px 0; border-top: 1px solid var(--color-border-subtle); }
.quick-links a:first-child { border-top: 0; padding-top: 0; }
.quick-links a:last-child { padding-bottom: 0; }
.quick-links a > .icon:first-child { color: var(--color-primary); }
.quick-links a > .icon:last-child { color: var(--color-muted); }
.quick-links span { display: grid; gap: 2px; }
.quick-links strong { font-size: 12px; }
.quick-links small { color: var(--color-muted); font-size: 11px; }
.leaderboard-panel :deep(.data-table), .leaderboard-panel :deep(.data-table-scroll) { min-width: 0; }
@media (max-width: 560px) {
  .admin-heading { align-items: stretch; flex-direction: column; }
  .admin-heading h1 { font-size: 23px; }
  .admin-heading__actions { display: grid; grid-template-columns: 1fr 1fr; }
  .admin-heading__actions > * { min-width: 0; padding-inline: 8px; font-size: 11px; }
  .admin-now { grid-template-columns: 1fr; }
  .admin-now > * + * { border-top: 1px solid var(--color-border); border-left: 0; }
  .admin-now__facts { padding-block: 14px; }
  .admin-now__facts > div + div { padding-left: 14px; }
  .clock-control { padding: 15px; }.clock-control .section-block__head { flex-direction: column; }.clock-control__body, .period-switch { grid-template-columns: 1fr; }.period-switch__apply { grid-template-columns: 1fr 1fr; }.period-switch__apply button { white-space: normal; }
  .admin-dashboard, .admin-operations { grid-template-columns: 1fr; }
  .leaderboard-panel :deep(.data-table),
  .leaderboard-panel :deep(.data-table thead),
  .leaderboard-panel :deep(.data-table tbody),
  .leaderboard-panel :deep(.data-table tr),
  .leaderboard-panel :deep(.data-table td) { display: block; width: 100%; }
  .leaderboard-panel :deep(.data-table thead) { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  .leaderboard-panel :deep(.data-table tr) { padding: 12px 0; border-top: 1px solid var(--color-border-subtle); }
  .leaderboard-panel :deep(.data-table tr:first-child) { border-top: 0; }
  .leaderboard-panel :deep(.data-table td),
  .leaderboard-panel :deep(.data-table td:first-child),
  .leaderboard-panel :deep(.data-table td:last-child) { display: grid; grid-template-columns: 72px minmax(0, 1fr); align-items: center; gap: 10px; padding: 6px 0; border-top: 0; text-align: left; }
  .leaderboard-panel :deep(.data-table td::before) { color: var(--color-muted); content: attr(data-label); font-size: 11px; font-weight: 800; }
  .leaderboard-panel :deep(.team-cell) { min-width: 0; }
  .leaderboard-panel :deep(.rank-bar) { width: min(100%, 180px); min-width: 0; }
}
</style>
