<template>
  <GameShell
    role-label="總召控制台"
    identity="活米村・開局設定"
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
      <button class="ghost-button" :class="{ 'is-loading': loading }" type="button" :disabled="loading" :aria-busy="loading" @click="loadSetup"><Icon name="clock" size="sm" />重新讀取</button>
      <button class="action-button" :class="{ 'is-loading': saving }" type="button" :disabled="saving || isDemo" :aria-busy="saving" @click="saveSetup"><Icon name="check" size="sm" />{{ saving ? '儲存中…' : '儲存開局設定' }}</button>
    </template>

    <div class="setup-lock">
      <Icon name="alert" size="sm" />
      <span v-if="isDemo">目前是展示資料。使用總召代碼登入後，才會讀取並寫入 Supabase 的實際場次設定。</span>
      <span v-else>場次狀態：<strong>{{ statusLabel }}</strong>。只有 draft／scheduled 可以修改開局資產；遊戲開始後所有設定會鎖定。</span>
    </div>

    <div v-if="message" class="form-message" :class="{ 'is-error': messageType === 'error' }"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</div>

    <div class="setup-tabs-shell">
      <div class="setup-tabs" role="tablist" aria-label="開局設定分類" @keydown="handleSetupTabKeydown">
        <button v-for="tab in setupTabs" :id="`setup-tab-${tab.id}`" :key="tab.id" class="setup-tab" :class="{ 'is-selected': activeSetupTab === tab.id }" type="button" role="tab" :aria-selected="activeSetupTab === tab.id" :aria-controls="activeSetupTab === tab.id ? `setup-panel-${tab.id}` : undefined" :tabindex="activeSetupTab === tab.id ? 0 : -1" @click="selectSetupTab(tab.id)">
          <Icon :name="tab.icon" size="sm" />
          <span class="setup-tab__copy"><strong>{{ tab.label }}</strong><small>{{ tab.hint }}</small></span>
          <span class="setup-tab__meta">{{ tab.meta }}</span>
        </button>
      </div>
    </div>

    <div class="setup-tab-panel" role="tabpanel" tabindex="0" :id="`setup-panel-${activeSetupTab}`" :aria-labelledby="`setup-tab-${activeSetupTab}`">

    <section v-if="activeSetupTab === 'products'" class="section-block config-editor">
      <div class="section-block__head"><div><h2>商品目錄</h2><p>交易識別碼、商品名稱、簡稱與單位都可以調整；保存時會同步歷史庫存、行情與交易紀錄。</p></div><span class="status-badge is-warning">{{ resources.length }} 項商品</span></div>
      <div class="product-config-grid">
        <article v-for="product in resources" :key="product.key" class="product-config-item">
          <div class="product-config-item__head"><span class="team-badge">{{ product.short_name }}</span><div><strong>{{ product.key }}</strong><span>目前交易紀錄識別碼</span></div></div>
          <div class="form-grid product-config-fields">
            <label class="form-field"><span>交易識別碼</span><input v-model.trim="product.key" type="text" maxlength="40" pattern="[a-z][a-z0-9_]{1,39}" placeholder="例如 phoenix_egg" /><small>小寫英文開頭，可用數字與底線</small></label>
            <label class="form-field"><span>商品名稱</span><input v-model.trim="product.name" type="text" maxlength="40" /></label>
            <label class="form-field"><span>簡稱</span><input v-model.trim="product.short_name" type="text" maxlength="6" /></label>
            <label class="form-field"><span>計量單位</span><input v-model.trim="product.unit_name" type="text" maxlength="8" /></label>
          </div>
        </article>
      </div>
    </section>

    <section v-if="activeSetupTab === 'rules'" class="section-block config-editor">
      <div class="section-block__head"><div><h2>遊戲規則</h2><p>這裡的數值會由後端套用到交易、挑戰、獎勵與黑心商人；保存後才會生效。</p></div><span class="status-badge is-neutral">可逐場設定</span></div>
      <div class="rules-grid">
        <div class="rule-group"><div class="rule-group__title"><Icon name="clock" size="sm" /><strong>時段與交易</strong></div><div class="form-grid two-up"><label class="form-field"><span>時段數</span><input v-model.number="setup.config.rules.period_count" type="number" min="1" max="4" /></label><label class="form-field"><span>每段分鐘</span><input v-model.number="setup.config.rules.period_duration_minutes" type="number" min="1" max="120" /></label><label class="form-field"><span>預設交易商品數</span><input v-model.number="setup.config.rules.trade_quantity" type="number" min="1" max="10" /></label><label class="check-field"><input v-model="setup.config.rules.same_market_trade_block" type="checkbox" /><span>禁止連續在同一市場交易</span></label></div></div>
        <div class="rule-group"><div class="rule-group__title"><Icon name="map" size="sm" /><strong>據點挑戰與佔領</strong></div><div class="form-grid two-up"><label class="form-field"><span>開放時段</span><input v-model.number="setup.config.rules.challenge_start_period" type="number" min="1" max="4" /></label><label class="form-field"><span>開放據點難度</span><input v-model.number="setup.config.rules.challenge_default_difficulty" type="number" min="1" max="5" /></label><label class="form-field"><span>已佔領據點難度</span><input v-model.number="setup.config.rules.challenge_occupied_difficulty" type="number" min="1" max="5" /></label><label class="form-field"><span>失敗冷卻（分鐘）</span><input v-model.number="setup.config.rules.challenge_cooldown_minutes" type="number" min="0" max="120" /></label><label class="form-field"><span>佔領收益／分鐘</span><input v-model.number="setup.config.rules.ownership_rate_per_minute" type="number" min="0" max="1000" /></label></div></div>
        <div class="rule-group"><div class="rule-group__title"><Icon name="spark" size="sm" /><strong>隱藏魔王</strong></div><div class="form-grid"><label class="form-field"><span>開放時段</span><input v-model.number="setup.config.rules.magic_start_period" type="number" min="1" max="4" /></label><div class="reward-editor"><span class="form-label">各難度獎勵（金幣）</span><div class="reward-editor__grid"><label v-for="(reward, index) in setup.config.rules.magic_reward_by_difficulty" :key="index" class="form-field"><span>{{ roman(index + 1) }}</span><input v-model.number="setup.config.rules.magic_reward_by_difficulty[index]" type="number" min="0" max="1000" /></label></div></div></div></div>
        <div class="rule-group"><div class="rule-group__title"><Icon name="wallet" size="sm" /><strong>黑心商人與現場確認</strong></div><div class="form-grid two-up"><label class="form-field"><span>開放時段</span><input v-model.number="setup.config.rules.black_market_start_period" type="number" min="1" max="4" /></label><label class="form-field"><span>抽卡費用</span><input v-model.number="setup.config.rules.black_market_draw_cost" type="number" min="0" max="100000" /></label><label class="check-field"><input v-model="setup.config.rules.guard_money_pouch" type="checkbox" /><span>交易／挑戰需出示金錢袋</span></label><label class="check-field"><input v-model="setup.config.rules.guard_minimum_team_present" type="checkbox" /><span>交易／挑戰需半數隊員在場</span></label></div></div>
      </div>
      <div class="notice config-editor__notice"><Icon name="alert" size="sm" /><span>為避免現場規則互相矛盾，時段數目前最多 4 段；商品交易識別碼、名稱、簡稱、單位與行情都可自由調整。</span></div>
    </section>

    <section v-if="activeSetupTab === 'session'" class="section-block">
      <div class="section-block__head"><div><h2>場次資訊</h2><p>由 bootstrap 建立；這裡先確認目前場次狀態</p></div><span class="status-badge" :class="setup.session.status === 'draft' ? 'is-neutral' : 'is-warning'">{{ statusLabel }}</span></div>
      <div class="form-grid two-up"><label class="form-field"><span>場次名稱</span><input :value="setup.session.name" type="text" readonly /></label><label class="form-field"><span>預定開始</span><input :value="formattedSchedule" type="text" readonly placeholder="手動開始" /></label></div>
    </section>

      <section v-if="activeSetupTab === 'session'" class="section-block access-password-section">
        <div class="section-block__head">
          <div><h2>登入密碼管理</h2><p>總召可以替魔王、關主與隊輔設定登入密碼；總召密碼維持場次建立時的預設密碼。留白代表不修改，既有密碼不會回顯。</p></div>
          <div class="access-password-section__badges"><span class="status-badge is-neutral">總召專用</span><span class="status-badge is-warning">敏感資訊</span></div>
        </div>

        <div class="notice access-password-notice"><Icon name="alert" size="sm" /><span v-if="isDemo">目前是展示資料。使用總召登入後，才可設定實際場次的登入密碼。</span><span v-else>密碼只保存於伺服器的雜湊值；儲存或輪替後原密碼立即失效。</span></div>

        <div class="password-management-subhead"><div><h3>隱藏魔王密碼</h3><p>輪替後舊密碼會立即失效；新密碼只在這次操作後顯示，請交給現場魔王。</p></div><span class="status-badge is-warning">一次性顯示</span></div>
        <div class="role-code-row"><div class="notice"><Icon name="spark" size="sm" /><span v-if="magicBossCode">本次魔王密碼：<strong class="one-time-code">{{ magicBossCode }}</strong></span><span v-else>尚未在這裡顯示魔王密碼。</span></div><button class="ghost-button" :class="{ 'is-loading': rotatingCode }" type="button" :disabled="rotatingCode || isDemo" :aria-busy="rotatingCode" @click="rotateBossCode">{{ rotatingCode ? '產生中…' : '輪替並顯示新密碼' }}</button></div>

        <div class="password-management-divider" aria-hidden="true"></div>
        <div class="password-management-subhead"><div><h3>現場身分密碼</h3><p>只會更新有輸入新密碼的身分；總召密碼不在此處修改。</p></div><span class="mini-label">共 {{ accessCodes.length }} 個可設定身分</span></div>
        <div class="access-password-list"><article v-for="accessCode in accessCodes" :key="accessCode.access_id" class="access-password-item"><div class="access-password-item__identity"><span class="status-badge is-neutral">{{ roleLabel(accessCode.role) }}</span><strong>{{ accessCode.display_name }}</strong></div><label class="form-field access-password-item__field"><span>設定新密碼</span><input v-model="passwordDrafts[accessCode.access_id]" type="password" minlength="4" maxlength="64" autocomplete="new-password" placeholder="至少 4 個字元" :disabled="isDemo || passwordSaving" /></label></article></div><div class="access-password-actions"><span>密碼儲存後，原密碼立即失效。</span><button class="ghost-button" :class="{ 'is-loading': passwordSaving }" type="button" :disabled="passwordSaving || isDemo" :aria-busy="passwordSaving" @click="saveAccessPasswords">{{ passwordSaving ? '儲存中…' : '儲存登入密碼' }}</button></div>
      </section>

    <div class="setup-tab-stack">
      <section v-if="activeSetupTab === 'teams'" class="section-block team-profile-editor">
        <div class="section-block__head"><div><h2>8 個學院／小隊</h2><p>這些資料會顯示在首頁；金幣與商品則會在開局前寫入每隊錢包。</p></div><span class="mini-label">{{ setup.teams.length }} / 8 隊</span></div>
        <div class="team-profile-grid">
          <article v-for="team in setup.teams" :key="team.number" class="team-profile-card">
            <div class="team-profile-card__head"><span class="team-profile-card__icon" :class="`team-profile-card__icon--${team.tone}`">{{ team.icon }}</span><div><strong>第 {{ team.number }} 隊</strong><span>首頁公開資料</span></div></div>
            <div class="form-grid team-profile-fields">
              <label class="form-field"><span>圖示</span><input v-model.trim="team.icon" type="text" maxlength="4" placeholder="✦" /></label>
              <label class="form-field"><span>學院／小隊名稱</span><input v-model.trim="team.name" type="text" maxlength="40" /></label>
              <label class="form-field"><span>英文名稱</span><input v-model.trim="team.english_name" type="text" maxlength="40" placeholder="AURORA" /></label>
              <label class="form-field team-profile-fields__wide"><span>描述／特質</span><textarea v-model.trim="team.description" rows="2" maxlength="120" placeholder="例如：智慧與學習"></textarea></label>
              <label class="form-field"><span>視覺色調</span><select v-model="team.tone"><option value="aurora">極光藍</option><option value="ignis">焰心紅</option><option value="terra">大地綠</option><option value="aqua">潮汐青</option><option value="nova">星耀紫</option><option value="solis">日冕金</option><option value="ventus">風行綠</option><option value="luna">月影藍</option></select></label>
            </div>
            <div class="team-profile-card__assets"><label class="form-field"><span>初始金幣</span><input v-model.number="team.initial_money" type="number" min="0" /></label><label v-for="resource in resources" :key="resource.key" class="form-field"><span>{{ resource.short_name }}</span><input v-model.number="team.initial_inventory[resource.key]" type="number" min="0" /></label></div>
          </article>
        </div>
      </section>

      <section v-if="activeSetupTab === 'markets'" class="section-block"><div class="section-block__head"><div><h2>8 個市場位置</h2><p>地圖座標使用 0–100 的相對百分比</p></div><span class="mini-label">{{ setup.markets.length }} / 8 市場</span></div><div class="setup-list"><div v-for="market in setup.markets" :key="market.code" class="setup-row setup-row--market"><span class="setup-index">{{ market.code }}</span><label class="form-field"><span>市場名稱</span><input v-model="market.name" type="text" maxlength="40" /></label><label class="form-field"><span>X</span><input v-model.number="market.map_x" type="number" min="0" max="100" /></label><label class="form-field"><span>Y</span><input v-model.number="market.map_y" type="number" min="0" max="100" /></label></div></div></section>
    </div>

    <section v-if="activeSetupTab === 'rates'" class="section-block rates-editor">
      <div class="section-block__head">
        <div><h2>商會行情設定</h2><p>選擇時段後，一次編輯所有商會的 4 種商品；每筆價格都會獨立保存。</p></div>
        <div class="rate-summary" aria-label="行情設定摘要"><span><strong>{{ enabledBuyRateCount }}</strong> / {{ totalRateCount }} 筆可買入</span><span><strong>{{ publicRateCount }}</strong> 筆公開價格</span></div>
      </div>

      <div class="rates-toolbar">
        <div class="period-tabs" role="tablist" aria-label="選擇編輯時段">
          <button v-for="period in periods" :key="period" class="period-tab" :class="{ 'is-selected': selectedPeriod === period }" type="button" role="tab" :aria-selected="selectedPeriod === period" @click="selectedPeriod = period">
            <span>第 {{ period }} 時段</span><small>{{ periodSummary(period) }}</small>
          </button>
        </div>
        <label class="market-filter"><span>顯示商會</span><select v-model="selectedMarket" class="setup-select" aria-label="篩選商會"><option value="all">全部商會（{{ setup.markets.length }}）</option><option v-for="market in setup.markets" :key="market.code" :value="market.code">{{ market.code }}・{{ market.name }}</option></select></label>
      </div>

      <div class="notice rates-editor__notice"><Icon name="alert" size="sm" /><span><strong>買入價設為 0 = 停止隊伍向該商會買入此商品。</strong>公開價格預設開啟；關閉後只有總召與對應關主看得到。</span></div>

      <div class="rate-table-wrap">
        <table class="data-table setup-rate-table">
          <colgroup>
            <col class="setup-rate-table__col setup-rate-table__col--market" />
            <col class="setup-rate-table__col setup-rate-table__col--product" />
            <col class="setup-rate-table__col setup-rate-table__col--price" />
            <col class="setup-rate-table__col setup-rate-table__col--price" />
            <col class="setup-rate-table__col setup-rate-table__col--public" />
          </colgroup>
          <thead><tr><th>商會</th><th>商品</th><th>買入價<small>隊伍向商會買</small></th><th>售出價<small>隊伍向商會賣</small></th><th>隊伍端價格</th></tr></thead>
          <tbody>
            <template v-for="market in visibleMarkets" :key="market.code">
              <tr v-for="resource in resources" :key="`${market.code}-${resource.key}`">
                <td v-if="resource.key === resources[0]?.key" class="market-cell" :rowspan="resources.length"><div class="market-cell__content"><div class="market-row__name"><span class="market-code">{{ market.code }}</span><div><strong>{{ market.name }}</strong><span>第 {{ selectedPeriod }} 時段</span></div></div><span class="status-badge" :class="marketEnabledCount(market.code) ? 'is-success' : 'is-neutral'">{{ marketEnabledCount(market.code) }} / {{ resources.length }} 可買</span></div></td>
                <td><div class="team-cell"><span class="team-badge">{{ resource.short_name }}</span><div><strong>{{ resource.name }}</strong><span>預設 {{ setup.config.rules.trade_quantity }} {{ resource.unit_name }}</span></div></div></td>
                <td><label class="price-field"><span class="sr-only">{{ market.name }}・{{ resource.name }} 買入價</span><input v-model.number="rateFor(market.code, selectedPeriod, resource.key).buy_price" class="table-input" type="number" min="0" inputmode="numeric" @blur="normalizePrice(rateFor(market.code, selectedPeriod, resource.key), 'buy_price')" /><span>枚</span></label><small v-if="rateFor(market.code, selectedPeriod, resource.key).buy_price === 0" class="rate-status">停止買入</small></td>
                <td><label class="price-field"><span class="sr-only">{{ market.name }}・{{ resource.name }} 售出價</span><input v-model.number="rateFor(market.code, selectedPeriod, resource.key).sell_price" class="table-input" type="number" min="0" inputmode="numeric" @blur="normalizePrice(rateFor(market.code, selectedPeriod, resource.key), 'sell_price')" /><span>枚</span></label></td>
                <td><label class="toggle-field"><input v-model="rateFor(market.code, selectedPeriod, resource.key).is_public" type="checkbox" /><span>{{ rateFor(market.code, selectedPeriod, resource.key).is_public ? '公開顯示' : '僅關主可見' }}</span></label></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </section>
    </div>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, getAccessCodes, getSetup, roleLabel, rotateMagicBossCode, updateAccessCodePasswords, updateConfig, updateMarkets, updateRates, updateTeams } from '@/lib/api'
import { cloneDefaultConfig } from '@/lib/gameConfig'
import { useSession } from '@/lib/session'
import type { AccessCodeSummary, ResourceKey, SetupMarket, SetupRate, SetupSnapshot, SetupTeam } from '@/types/game'

const router = useRouter()
const route = useRoute()
const { state } = useSession()
const navItems = [{ to: '/admin', label: '總覽', icon: 'dashboard' }, { to: '/admin/setup', label: '開局設定', icon: 'spark' }, { to: '/admin/markets', label: '市場與行情', icon: 'market' }, { to: '/admin/teams', label: '隊伍資產', icon: 'team' }, { to: '/admin/map', label: '地圖與佔領', icon: 'map' }]
type SetupTabId = 'session' | 'products' | 'rules' | 'teams' | 'markets' | 'rates'
type SetupTab = { id: SetupTabId; label: string; hint: string; icon: string; meta: string }

const setup = reactive<SetupSnapshot>(demoSetup())
const resources = computed(() => setup.config.products)
const loading = ref(false)
const saving = ref(false)
const rotatingCode = ref(false)
const magicBossCode = ref('')
const accessCodes = ref<AccessCodeSummary[]>(demoAccessCodes())
const passwordDrafts = reactive<Record<string, string>>({})
const passwordSaving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const selectedMarket = ref('all')
const selectedPeriod = ref(1)
const activeSetupTab = ref<SetupTabId>('session')
const routeTabByPath: Record<string, SetupTabId> = { '/admin/setup': 'session', '/admin/markets': 'rates', '/admin/teams': 'teams', '/admin/map': 'markets' }
const isDemo = computed(() => !state.token || state.identity?.role !== 'coordinator')
const periods = computed(() => Array.from({ length: setup.config.rules.period_count }, (_, index) => index + 1))
const visibleMarkets = computed(() => selectedMarket.value === 'all' ? setup.markets : setup.markets.filter((market) => market.code === selectedMarket.value))
const totalRateCount = computed(() => setup.markets.length * resources.value.length * periods.value.length)
const configuredRates = computed(() => setup.rates.filter((rate) => periods.value.includes(rate.period)))
const enabledBuyRateCount = computed(() => configuredRates.value.filter((rate) => rate.buy_price > 0).length)
const publicRateCount = computed(() => configuredRates.value.filter((rate) => rate.is_public).length)
const statusLabel = computed(() => ({ draft: '尚未開始', scheduled: '已排程', running: '進行中', paused: '暫停中', finished: '已結束' }[setup.session.status]))
const formattedSchedule = computed(() => setup.session.scheduled_start ? new Date(setup.session.scheduled_start).toLocaleString('zh-TW', { dateStyle: 'medium', timeStyle: 'short' }) : '手動開始')
const setupTabs = computed<SetupTab[]>(() => [
  { id: 'session', label: '場次設定', hint: '狀態與權限', icon: 'spark', meta: statusLabel.value },
  { id: 'products', label: '商品目錄', hint: '名稱與識別碼', icon: 'wallet', meta: `${resources.value.length} 項` },
  { id: 'rules', label: '遊戲規則', hint: '時段與玩法', icon: 'clock', meta: '4 組' },
  { id: 'teams', label: '隊伍資產', hint: '金幣與物資', icon: 'team', meta: `${setup.teams.length} 隊` },
  { id: 'markets', label: '市場位置', hint: '地圖座標', icon: 'map', meta: `${setup.markets.length} 個` },
  { id: 'rates', label: '商會行情', hint: '各段交易價格', icon: 'market', meta: `${totalRateCount.value} 筆` },
])
const activeSetupTabIndex = computed(() => Math.max(0, setupTabs.value.findIndex((tab) => tab.id === activeSetupTab.value)))

ensureAllRateRows()
watch(() => route.path, (path) => { activeSetupTab.value = routeTabByPath[path] || 'session' }, { immediate: true })
onMounted(loadSetup)

function selectSetupTab(tabId: SetupTabId) {
  activeSetupTab.value = tabId
}

function handleSetupTabKeydown(event: KeyboardEvent) {
  const key = event.key
  if (!['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'].includes(key)) return
  event.preventDefault()

  const lastIndex = setupTabs.value.length - 1
  const nextIndex = key === 'Home'
    ? 0
    : key === 'End'
      ? lastIndex
      : (activeSetupTabIndex.value + (key === 'ArrowRight' || key === 'ArrowDown' ? 1 : -1) + setupTabs.value.length) % setupTabs.value.length
  const nextTab = setupTabs.value[nextIndex]
  if (!nextTab) return
  selectSetupTab(nextTab.id)
  window.requestAnimationFrame(() => document.getElementById(`setup-tab-${nextTab.id}`)?.focus())
}

async function loadSetup() {
  message.value = ''
  if (isDemo.value || !state.identity || !state.token) return
  loading.value = true
  try {
    const [nextSetup, nextAccessCodes] = await Promise.all([getSetup(state.identity.session_id, state.token), getAccessCodes(state.identity.session_id, state.token)])
    Object.assign(setup, nextSetup)
    accessCodes.value = nextAccessCodes
    initializePasswordDrafts()
    ensureAllRateRows()
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
    ensureAllRateRows()
    validateConfig()
    await updateConfig(sessionId, setup.config, state.token)
    await updateTeams(sessionId, setup.teams, state.token)
    await updateMarkets(sessionId, setup.markets, state.token)
    await updateRates(sessionId, setup.rates, state.token)
    messageType.value = 'success'
    message.value = '開局設定已保存，下一步可由總召控制時鐘。'
  } catch (error) {
    showError(error)
  } finally {
    saving.value = false
  }
}

async function rotateBossCode() {
  if (isDemo.value || !state.identity || !state.token) return
  rotatingCode.value = true
  try {
    magicBossCode.value = (await rotateMagicBossCode(state.identity.session_id, state.token)).code
    accessCodes.value = await getAccessCodes(state.identity.session_id, state.token)
    initializePasswordDrafts()
    messageType.value = 'success'
    message.value = '魔王密碼已輪替，請立即抄錄並交給現場魔王。'
  } catch (error) {
    showError(error)
  } finally {
    rotatingCode.value = false
  }
}

async function saveAccessPasswords() {
  if (isDemo.value || !state.identity || !state.token) {
    showError(new Error('請使用總召登入後再設定其他身分的登入密碼。'))
    return
  }
  const passwords = accessCodes.value
    .map((accessCode) => ({ access_id: accessCode.access_id, password: passwordDrafts[accessCode.access_id] || '' }))
    .filter((item) => item.password.length > 0)
  if (!passwords.length) {
    showError(new Error('請至少輸入一組要更新的登入密碼。'))
    return
  }
  const invalid = passwords.find((item) => item.password.trim().length === 0 || item.password.length < 4)
  if (invalid) {
    showError(new Error('登入密碼至少需要 4 個字元，且不可只有空白。'))
    return
  }
  passwordSaving.value = true
  message.value = ''
  try {
    const result = await updateAccessCodePasswords(state.identity.session_id, passwords, state.token)
    passwords.forEach((item) => { passwordDrafts[item.access_id] = '' })
    messageType.value = 'success'
    message.value = `已更新 ${result.updated} 個身分的登入密碼，原密碼已失效。`
  } catch (error) {
    showError(error)
  } finally {
    passwordSaving.value = false
  }
}

function initializePasswordDrafts() {
  accessCodes.value.forEach((accessCode) => {
    if (passwordDrafts[accessCode.access_id] === undefined) passwordDrafts[accessCode.access_id] = ''
  })
}

function ensureAllRateRows() {
  const marketCodes = setup.markets.map((market) => market.code)
  for (const marketCode of marketCodes) {
    for (const period of periods.value) {
      for (const resource of resources.value) {
        if (!setup.rates.some((rate) => rate.market_code === marketCode && rate.period === period && rate.resource_type === resource.key)) {
          setup.rates.push({ market_code: marketCode, period, resource_type: resource.key, buy_price: 0, sell_price: 0, is_public: true })
        }
      }
    }
  }
}

watch(() => setup.config.rules.period_count, (count) => {
  if (selectedPeriod.value > count) selectedPeriod.value = count
  ensureAllRateRows()
})

watch(() => setup.config.products.map((product) => product.key), (keys, previousKeys) => {
  if (!previousKeys) return
  keys.forEach((newKey, index) => {
    const oldKey = previousKeys[index]
    if (!oldKey || oldKey === newKey) return
    setup.teams.forEach((team) => {
      if (team.initial_inventory[newKey] === undefined) team.initial_inventory[newKey] = team.initial_inventory[oldKey] || 0
      delete team.initial_inventory[oldKey]
    })
    setup.rates.forEach((rate) => {
      if (rate.resource_type === oldKey) rate.resource_type = newKey
    })
  })
})

function validateConfig() {
  const keys = resources.value.map((product) => product.key.trim())
  if (keys.some((key) => !/^[a-z][a-z0-9_]{1,39}$/.test(key)) || new Set(keys).size !== keys.length) throw new Error('商品交易識別碼需以小寫英文開頭，只能包含小寫英文、數字與底線，且不可重複。')
  const names = resources.value.map((product) => product.name.trim())
  if (names.some((name) => !name) || new Set(names).size !== names.length) throw new Error('商品名稱必須填寫且不可重複。')
  const rules = setup.config.rules
  if (rules.challenge_start_period > rules.period_count || rules.magic_start_period > rules.period_count || rules.black_market_start_period > rules.period_count) {
    throw new Error('各玩法開放時段不可晚於總時段數。')
  }
}

function roman(level: number) { return ['I', 'II', 'III', 'IV', 'V'][level - 1] }

function rateFor(marketCode: string, period: number, resource: ResourceKey) {
  const existing = setup.rates.find((rate) => rate.market_code === marketCode && rate.period === period && rate.resource_type === resource)
  if (existing) return existing
  const fallback: SetupRate = { market_code: marketCode, period, resource_type: resource, buy_price: 0, sell_price: 0, is_public: true }
  setup.rates.push(fallback)
  return fallback
}

function periodSummary(period: number) {
  const rates = setup.rates.filter((rate) => rate.period === period)
  return `${rates.filter((rate) => rate.buy_price > 0).length} 筆可買`
}

function marketEnabledCount(marketCode: string) {
  return setup.rates.filter((rate) => rate.market_code === marketCode && rate.period === selectedPeriod.value && rate.buy_price > 0).length
}

function normalizePrice(rate: SetupRate, field: 'buy_price' | 'sell_price') {
  const value = Number(rate[field])
  rate[field] = Number.isFinite(value) && value >= 0 ? Math.floor(value) : 0
}

function showError(error: unknown) {
  messageType.value = 'error'
  message.value = error instanceof ApiError ? error.message : error instanceof Error ? error.message : '設定讀取失敗，請稍後再試。'
}

function goLogin() { router.push('/login') }

function demoSetup(): SetupSnapshot {
  const profiles: Array<{ name: string; english_name: string; icon: string; description: string; tone: string }> = [
    { name: '極光院', english_name: 'AURORA', icon: '✦', description: '智慧與學習', tone: 'aurora' }, { name: '焰心院', english_name: 'IGNIS', icon: '♜', description: '勇氣與膽識', tone: 'ignis' }, { name: '大地院', english_name: 'TERRA', icon: '⌁', description: '企圖與韌性', tone: 'terra' }, { name: '潮汐院', english_name: 'AQUA', icon: '♒', description: '忠誠與團結', tone: 'aqua' },
    { name: '星耀院', english_name: 'NOVA', icon: '✧', description: '好奇與創造', tone: 'nova' }, { name: '日冕院', english_name: 'SOLIS', icon: '☼', description: '熱情與專注', tone: 'solis' }, { name: '風行院', english_name: 'VENTUS', icon: '◇', description: '自由與協作', tone: 'ventus' }, { name: '月影院', english_name: 'LUNA', icon: '☽', description: '觀察與直覺', tone: 'luna' },
  ]
  const teams: SetupTeam[] = profiles.map((profile, index) => ({ id: `demo-team-${index + 1}`, number: index + 1, ...profile, initial_money: 100, initial_inventory: { dragon_egg: 2, time_device: 1, unicorn_blood: 2, basilisk_fang: 0 } }))
  const markets: SetupMarket[] = Array.from({ length: 8 }, (_, index) => { const code = String.fromCharCode(65 + index); return { id: `demo-market-${index}`, code, name: code, map_x: 15 + (index % 4) * 23, map_y: 20 + Math.floor(index / 4) * 55 } })
  return { session: { id: 'demo-session', name: '活米村・Orientation 2026', status: 'draft', scheduled_start: null, current_period: 0 }, config: cloneDefaultConfig(), teams, markets, rates: [] }
}

function demoAccessCodes(): AccessCodeSummary[] {
  const markets = Array.from({ length: 8 }, (_, index) => String.fromCharCode(65 + index)).map((code) => ({ access_id: `demo-market-${code}`, role: 'market_master' as const, display_name: `${code} 市場`, market_id: `demo-market-${code}`, team_id: null, active: true }))
  const teams = Array.from({ length: 8 }, (_, index) => ({ access_id: `demo-team-${index + 1}`, role: 'team_facilitator' as const, display_name: `第 ${index + 1} 隊`, team_id: `demo-team-${index + 1}`, market_id: null, active: true }))
  return [{ access_id: 'demo-magic-boss', role: 'magic_boss', display_name: '隱藏魔王工作台', team_id: null, market_id: null, active: true }, ...markets, ...teams]
}
</script>

<style scoped>
.setup-tabs-shell { margin-bottom: 16px; padding-top: 10px; border-bottom: 1px solid var(--color-border); }
.setup-tabs { display: flex; gap: 6px; overflow-x: auto; padding: 0 1px; scrollbar-width: thin; }
.setup-tab { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 9px; flex: 1 0 145px; min-height: 61px; padding: 10px 12px; color: var(--color-muted); background: var(--color-surface); border: 1px solid var(--color-border); border-bottom: 1px solid transparent; border-radius: var(--radius-sm) var(--radius-sm) 0 0; text-align: left; transition: color 160ms ease-out, background 160ms ease-out, border-color 160ms ease-out; }
.setup-tab:hover { color: var(--color-primary); background: var(--color-primary-soft); border-color: oklch(0.7 0.07 255 / .48); }
.setup-tab.is-selected { color: var(--color-ink); background: var(--color-surface-raised); border-color: var(--color-primary); border-bottom-color: var(--color-accent); }
.setup-tab .icon { color: var(--color-primary); }
.setup-tab__copy { display: grid; min-width: 0; gap: 3px; }
.setup-tab__copy strong { overflow: hidden; color: inherit; font-size: 13px; font-weight: 800; text-overflow: ellipsis; white-space: nowrap; }
.setup-tab__copy small { overflow: hidden; color: var(--color-muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.setup-tab__meta { color: var(--color-muted); font-size: 10px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.setup-tab.is-selected .setup-tab__meta { color: var(--color-primary-ink); font-weight: 800; }
.setup-tab-panel, .setup-tab-stack { display: grid; gap: 16px; min-width: 0; }
.config-editor { display: grid; gap: 18px; }
.access-password-section { display: grid; gap: 16px; }
.access-password-section__badges { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; }
.access-password-notice { margin: 0; }
.password-management-subhead { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.password-management-subhead h3 { color: var(--color-ink); font-size: 14px; font-weight: 800; }
.password-management-subhead p { margin-top: 4px; color: var(--color-muted); font-size: 11px; line-height: 1.5; }
.password-management-divider { height: 1px; background: var(--color-border); }
.role-code-row { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
.role-code-row .notice { flex: 1; }
.role-code-row .ghost-button { flex: 0 0 auto; }
.one-time-code { color: var(--color-accent); font-size: 17px; letter-spacing: .12em; }
.access-password-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.access-password-item { display: grid; gap: 12px; padding: 14px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.access-password-item__identity { display: flex; align-items: center; gap: 8px; min-width: 0; }
.access-password-item__identity strong { overflow: hidden; color: var(--color-ink); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.access-password-item__field { gap: 6px; }
.access-password-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--color-muted); font-size: 11px; }
.product-config-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.product-config-item { display: grid; gap: 14px; padding: 16px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.product-config-item__head { display: flex; align-items: center; gap: 10px; }
.product-config-item__head strong, .product-config-item__head span { display: block; }
.product-config-item__head strong { color: var(--color-ink); font-size: 13px; }
.product-config-item__head span:last-child { margin-top: 3px; color: var(--color-muted); font-size: 11px; }
.product-config-fields { grid-template-columns: 1.2fr 1.4fr .7fr .7fr; gap: 10px; }
.rules-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.rule-group { display: grid; gap: 14px; padding: 16px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.rule-group__title { display: flex; align-items: center; gap: 8px; color: var(--color-primary-ink); font-size: 14px; }
.rule-group__title .icon { color: var(--color-primary); }
.check-field { display: flex; align-items: center; gap: 8px; min-height: 41px; color: var(--color-ink); font-size: 12px; }
.check-field input { width: 16px; height: 16px; accent-color: var(--color-primary); }
.form-label { display: block; margin-bottom: 7px; color: var(--color-ink); font-size: 12px; font-weight: 800; }
.reward-editor__grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 7px; }
.reward-editor__grid .form-field { gap: 5px; }
.reward-editor__grid .form-field > span { font-size: 11px; color: var(--color-muted); }
.config-editor__notice { margin-top: 0; }
.team-profile-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.team-profile-card { display: grid; gap: 16px; padding: 16px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.team-profile-card__head { display: flex; align-items: center; gap: 10px; }
.team-profile-card__head strong, .team-profile-card__head span { display: block; }
.team-profile-card__head strong { color: var(--color-ink); font-size: 13px; }
.team-profile-card__head span:last-child { margin-top: 3px; color: var(--color-muted); font-size: 11px; }
.team-profile-card__icon { display: grid; width: 40px; height: 40px; place-items: center; color: var(--team-profile-color, var(--color-primary)); border: 1px solid currentColor; border-radius: 50%; font-size: 20px; }
.team-profile-card__icon--aurora { --team-profile-color: oklch(.73 .1 235); }
.team-profile-card__icon--ignis { --team-profile-color: oklch(.7 .14 35); }
.team-profile-card__icon--terra { --team-profile-color: oklch(.68 .12 130); }
.team-profile-card__icon--aqua { --team-profile-color: oklch(.72 .12 210); }
.team-profile-card__icon--nova { --team-profile-color: oklch(.75 .12 300); }
.team-profile-card__icon--solis { --team-profile-color: oklch(.8 .14 78); }
.team-profile-card__icon--ventus { --team-profile-color: oklch(.72 .1 180); }
.team-profile-card__icon--luna { --team-profile-color: oklch(.78 .08 265); }
.team-profile-fields { grid-template-columns: minmax(72px, .55fr) minmax(0, 1.45fr); gap: 10px; }
.team-profile-fields__wide { grid-column: 1 / -1; }
.team-profile-fields textarea { width: 100%; min-height: 54px; padding: 9px 11px; resize: vertical; color: var(--color-ink); background: var(--color-surface-raised); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); outline: none; font: inherit; font-size: 12px; line-height: 1.5; }
.team-profile-fields textarea:focus { border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-soft); }
.team-profile-card__assets { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; padding-top: 14px; border-top: 1px solid var(--color-border); }
.setup-row--assets { grid-template-columns: 38px minmax(125px, 1fr) 90px repeat(4, 64px); align-items: end; }
.setup-row--market { grid-template-columns: 38px minmax(0, 1fr) 68px 68px; align-items: end; }
.setup-select { min-height: 36px; padding: 0 10px; color: var(--color-ink); background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: 12px; }
.rates-editor { display: grid; gap: 14px; min-width: 0; }
.rate-summary { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px 14px; color: var(--color-muted); font-size: 11px; text-align: right; }
.rate-summary strong { color: var(--color-primary); font-size: 15px; font-variant-numeric: tabular-nums; }
.rates-toolbar { display: flex; align-items: flex-end; justify-content: space-between; gap: 14px; }
.period-tabs { display: flex; flex-wrap: wrap; gap: 8px; }
.period-tab { display: grid; gap: 3px; min-width: 96px; min-height: 46px; padding: 7px 10px; color: var(--color-ink); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-sm); text-align: left; transition: color 160ms ease-out, background 160ms ease-out, border-color 160ms ease-out, transform 160ms ease-out; }
.period-tab:hover { border-color: var(--color-primary); background: var(--color-primary-soft); transform: translateY(-1px); }
.period-tab span { font-size: 13px; font-weight: 800; }
.period-tab small { color: var(--color-muted); font-size: 11px; }
.period-tab.is-selected { color: white; background: var(--color-primary); border-color: var(--color-primary); }
.period-tab.is-selected small { color: oklch(0.94 0.025 252); }
.market-filter { display: grid; gap: 6px; min-width: 180px; }
.market-filter > span { color: var(--color-muted); font-size: 11px; font-weight: 800; }
.rates-editor__notice { margin: 0; }
.rate-table-wrap { width: 100%; max-width: 100%; min-width: 0; overflow-x: auto; border: 1px solid var(--color-border); border-radius: var(--radius-sm); overscroll-behavior-inline: contain; }
.setup-rate-table { width: 100%; min-width: 860px; table-layout: fixed; }
.setup-rate-table__col--market { width: 170px; }
.setup-rate-table__col--product { width: 220px; }
.setup-rate-table__col--price { width: 150px; }
.setup-rate-table__col--public { width: 160px; }
.setup-rate-table th { padding: 8px 10px 7px; background: var(--color-surface); }
.setup-rate-table th small { display: block; margin-top: 2px; color: var(--color-muted); font-size: 10px; font-weight: 500; white-space: nowrap; }
.setup-rate-table td { padding: 7px 10px; }
.setup-rate-table th:first-child, .setup-rate-table td:first-child { padding-left: 10px; }
.setup-rate-table th:last-child, .setup-rate-table td:last-child { padding-right: 10px; text-align: left; }
.market-cell { width: 170px; vertical-align: top !important; background: var(--color-primary-soft); }
.market-cell__content { display: flex; flex-direction: column; justify-content: space-between; gap: 8px; height: 100%; min-height: 100%; }
.market-cell .market-row__name { align-items: flex-start; }
.market-cell .market-row__name div { min-width: 0; }
.market-cell .market-row__name strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.market-cell .status-badge { justify-self: start; }
.setup-rate-table .team-cell { min-width: 0; gap: 8px; }
.setup-rate-table .team-cell > div { min-width: 0; }
.setup-rate-table .team-cell strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.price-field { display: inline-flex; align-items: center; gap: 7px; }
.table-input { width: 76px; min-height: 32px; padding: 0 8px; color: var(--color-ink); background: var(--color-surface-raised); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); font-variant-numeric: tabular-nums; text-align: right; }
.table-input:focus { border-color: var(--color-primary); outline: none; box-shadow: 0 0 0 3px var(--color-primary-soft); }
.price-field > span:last-child { color: var(--color-muted); font-size: 11px; }
.rate-status { display: block; margin-top: 2px; color: var(--color-warning); font-size: 10px; line-height: 1.3; }
.toggle-field { display: inline-flex; align-items: center; gap: 7px; max-width: 100%; color: var(--color-muted); font-size: 12px; white-space: nowrap; }
.toggle-field input { width: 16px; height: 16px; accent-color: var(--color-primary); }
@media (max-width: 1040px) { .setup-row--assets { grid-template-columns: 30px minmax(120px, 1fr) 80px repeat(4, 58px); } .team-profile-grid { grid-template-columns: 1fr; } .rules-grid { grid-template-columns: 1fr; } }
@media (max-width: 760px) { .setup-tabs-shell { padding-top: 8px; } .setup-tab { flex-basis: 138px; } .product-config-grid { grid-template-columns: 1fr; } .product-config-fields { grid-template-columns: 1fr 1fr; } .product-config-fields .form-field:first-child, .product-config-fields .form-field:nth-child(2) { grid-column: 1 / -1; } .team-profile-fields { grid-template-columns: 1fr 1fr; } .team-profile-card__assets { grid-template-columns: repeat(2, minmax(0, 1fr)); } .setup-row--assets { grid-template-columns: 30px minmax(0, 1fr) 88px; } .setup-row--assets .form-field:nth-child(n + 4) { grid-column: 2 / span 2; } .setup-row--market { grid-template-columns: 30px minmax(0, 1fr) 64px 64px; } .rate-summary { justify-content: flex-start; text-align: left; } .rates-toolbar { align-items: stretch; flex-direction: column; } .period-tabs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); } .period-tab { min-width: 0; } .market-filter { min-width: 0; } .rate-table-wrap { width: calc(100% + 36px); max-width: none; margin-inline: -18px; border-width: 1px 0; border-radius: 0; } .setup-rate-table { min-width: 860px; } .role-code-row { align-items: stretch; flex-direction: column; } .role-code-row .ghost-button { width: 100%; } .password-management-subhead { flex-direction: column; gap: 8px; } .access-password-section__badges { justify-content: flex-start; } .access-password-list { grid-template-columns: 1fr; } .access-password-actions { align-items: stretch; flex-direction: column; } }
@media (max-width: 480px) {
  .setup-tab { flex-basis: 132px; min-height: 58px; }
  .setup-tab__meta { display: none; }
  .product-config-fields,
  .team-profile-fields,
  .reward-editor__grid { grid-template-columns: 1fr; }
  .product-config-fields .form-field:first-child, .product-config-fields .form-field:nth-child(2) { grid-column: auto; }
  .team-profile-fields__wide { grid-column: auto; }
  .setup-row--market,
  .setup-row--assets { grid-template-columns: 30px minmax(0, 1fr); align-items: end; }
  .setup-row--market .form-field,
  .setup-row--assets .form-field { grid-column: 2; }
  .setup-row--assets .form-field:nth-child(n + 4) { grid-column: 2; }
  .team-profile-card__assets { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .rate-summary { display: grid; gap: 4px; }
  .period-tabs { grid-template-columns: 1fr 1fr; }
  .rate-table-wrap { width: calc(100% + 28px); margin-inline: -14px; }
}
</style>
