<template>
  <GameShell
    :role-label="identityLabel"
    identity="活動現場工作台"
    :nav-items="navItems"
    :hide-page-heading="true"
    :connected="!isDemo"
    :demo="isDemo"
    :period="period"
    :elapsed-ms="activity.effective_elapsed_ms"
    :status="status"
    :money="0"
    @sign-out="goLogin"
  >
    <template #heading-actions>
      <button class="ghost-button" type="button" :disabled="loading" @click="loadData"><Icon name="clock" size="sm" />重新整理</button>
    </template>

    <div class="page-intro">
      <div><span class="eyebrow">現場操作</span><h1>{{ currentStage?.name || '活動工作台' }}</h1><p>{{ currentStage ? stageDescription(currentStage.stage_type) : '等待總召設定目前活動階段。' }}</p></div>
      <div class="stage-chip"><span>目前身分</span><strong>{{ identityLabel }}</strong><small>{{ currentStage ? `第 ${currentStage.sort_order} 階段` : '尚未開始' }}</small></div>
    </div>

    <div v-if="message" class="form-message" :class="{ 'is-error': messageType === 'error' }"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</div>
    <div v-if="currentStage?.stage_type === 'magic_village'" class="notice"><Icon name="spark" size="sm" /><span>目前是活米村階段。市場交易、據點佔領、魔王挑戰與即時同步沿用原本工作台；本頁保留活動排行榜。</span></div>
    <div v-if="!isDemo && !activeRoles.length" class="notice is-warning"><Icon name="alert" size="sm" /><span>目前 Google 帳號尚未被指派這個階段的現場身分，請聯絡總召。</span></div>

    <div class="workspace-grid">
      <section v-if="currentStage?.stage_type === 'icebreaker'" class="section-block icebreaker-panel">
        <div class="section-block__head"><div><h2>破冰分圈</h2><p>先輸入編號搜尋，再加入目前圈圈；同一圈重複加入會直接擋下。</p></div><span class="status-badge is-success">手機操作</span></div>
        <div class="icebreaker-toolbar">
          <label class="form-field"><span>第幾輪</span><input v-model.number="roundNumber" type="number" min="1" max="999" inputmode="numeric" /></label>
          <label class="form-field"><span>圈圈編號</span><input v-model.number="groupNumber" type="number" min="1" max="999" inputmode="numeric" /></label>
          <button class="ghost-button" type="button" :disabled="!canOperateIcebreaker" @click="loadRecommendations">更新推薦</button>
        </div>
        <label class="search-field"><span class="sr-only">搜尋參加者</span><input v-model.trim="participantQuery" type="search" inputmode="search" placeholder="輸入編號或姓名，例如 A001" autocomplete="off" /><small>{{ filteredParticipants.length }} 位符合</small></label>
        <div v-if="selectedMembers.length" class="selected-members"><div class="selected-members__head"><strong>目前圈圈・{{ selectedMembers.length }} 人</strong><button class="text-button" type="button" @click="selectedMembers = []">清空</button></div><div class="member-chip-list"><button v-for="id in selectedMembers" :key="id" class="member-chip" type="button" @click="removeMember(id)">{{ participantLabel(id) }} ×</button></div></div>
        <div class="candidate-list"><button v-for="person in filteredParticipants" :key="person.id" class="candidate-row" type="button" :disabled="selectedMembers.includes(person.id)" @click="addMember(person.id)"><span class="participant-number">{{ person.participant_no }}</span><span><strong>{{ person.display_name }}</strong><small>{{ person.college_name || '未分院' }}・{{ person.team_name || '未分隊' }}</small></span><span class="candidate-state">{{ selectedMembers.includes(person.id) ? '已加入' : '加入' }}</span></button><p v-if="!filteredParticipants.length" class="empty-state">找不到符合的參加者，請確認編號。</p></div>
        <div v-if="recommendations.length" class="recommendation-box"><div class="recommendation-box__head"><div><strong>推薦尚未同圈的人</strong><small>依歷史同圈次數排序，數字越小越適合優先加入</small></div><span>{{ recommendations.length }} 位</span></div><button v-for="person in recommendations.slice(0, 8)" :key="person.id" class="recommendation-row" type="button" :disabled="selectedMembers.includes(person.id)" @click="addMember(person.id)"><span>{{ person.participant_no }}</span><strong>{{ person.display_name }}</strong><small>{{ person.never_shared ? '尚未同圈' : `曾同圈 ${person.shared_count} 次` }}</small></button></div>
        <div v-if="icebreakerWarnings.length" class="warning-list"><span v-for="warning in icebreakerWarnings" :key="warning.participant_id"><Icon name="alert" size="sm" />{{ participantLabel(warning.participant_id) }} 過去曾與圈內成員同圈 {{ warning.shared_count }} 次</span></div>
        <button class="action-button primary-mobile-action" type="button" :disabled="!canOperateIcebreaker || saving || selectedMembers.length === 0" :class="{ 'is-loading': saving }" @click="saveGroup">{{ saving ? '記錄中…' : `記錄第 ${roundNumber} 輪・第 ${groupNumber} 圈` }}</button>
      </section>

      <section v-else-if="isScoringStage" class="section-block score-panel">
        <div class="section-block__head"><div><h2>快速加分</h2><p>每次操作建立一筆不可變更的分數事件；可對個人、小隊或學院計分。</p></div><span class="status-badge is-warning">{{ canScore ? '可記分' : '僅供查看' }}</span></div>
        <div class="target-tabs" role="tablist"><button v-for="tab in targetTabs" :key="tab.value" type="button" role="tab" :aria-selected="targetType === tab.value" :class="{ 'is-selected': targetType === tab.value }" @click="targetType = tab.value">{{ tab.label }}</button></div>
        <label class="search-field"><span class="sr-only">搜尋計分目標</span><input v-model.trim="targetQuery" type="search" placeholder="搜尋編號、姓名、隊伍或學院" /><small>{{ filteredTargets.length }} 個目標</small></label>
        <div class="target-list"><button v-for="target in filteredTargets" :key="targetId(target)" class="target-row" type="button" :class="{ 'is-selected': selectedTargetId === targetId(target) }" @click="selectedTargetId = targetId(target)"><span class="target-key">{{ targetCode(target) }}</span><span><strong>{{ targetLabel(target) }}</strong><small>{{ targetMeta(target) }}</small></span><Icon v-if="selectedTargetId === targetId(target)" name="check" size="sm" /></button><p v-if="!filteredTargets.length" class="empty-state">目前沒有可選的計分對象。</p></div>
        <div class="score-entry"><label class="form-field"><span>分數</span><input v-model.number="points" type="number" step="0.5" inputmode="decimal" placeholder="例如 10" /></label><label class="form-field score-note"><span>備註（選填）</span><input v-model.trim="scoreNote" type="text" maxlength="500" placeholder="例如：第三關完成" /></label></div>
        <button class="action-button primary-mobile-action" type="button" :disabled="!canScore || saving || !selectedTargetId || !Number.isFinite(points) || points === 0" :class="{ 'is-loading': saving }" @click="submitScore">{{ saving ? '送出中…' : `送出 ${points || 0} 分` }}</button>
      </section>

      <section v-else class="section-block waiting-panel"><div class="section-block__head"><div><h2>目前階段不需本工作台操作</h2><p>請依目前階段的現場安排操作，或等待總召切換到其他活動階段。</p></div><Icon name="clock" size="lg" /></div><div class="notice"><Icon name="alert" size="sm" /><span>排行榜仍會在下方顯示，並依階段倍率分開計算個人、小隊與學院總分。</span></div></section>

      <section class="section-block leaderboard-panel">
        <div class="section-block__head"><div><h2>活動排行榜</h2><p>{{ leaderboardScope }}</p></div><span class="status-badge is-neutral">倍率後總分</span></div>
        <div class="leaderboard-tabs" role="tablist"><button v-for="tab in leaderboardTabs" :key="tab.value" type="button" role="tab" :aria-selected="leaderboardTab === tab.value" :class="{ 'is-selected': leaderboardTab === tab.value }" @click="leaderboardTab = tab.value">{{ tab.label }}</button></div>
        <div class="leaderboard-list"><div v-for="(entry, index) in leaderboardEntries" :key="entry.target_id" class="leaderboard-row"><span class="rank-number">{{ index + 1 }}</span><span class="leaderboard-name"><strong>{{ entry.name }}</strong><small>{{ entryCode(entry) }}</small></span><span class="score-values"><strong>{{ formatPoints(entry.weighted_points) }}</strong><small>原始 {{ formatPoints(entry.raw_points) }}</small></span></div><p v-if="!leaderboardEntries.length" class="empty-state">還沒有這個層級的分數紀錄。</p></div>
      </section>
    </div>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, getActivity, getIcebreakerRecommendations, getLeaderboards, getParticipants, getScoreTargets, recordScore, saveIcebreakerGroup } from '@/lib/api'
import { roleLabel } from '@/lib/api'
import { useSession } from '@/lib/session'
import type { ActivitySnapshot, ActivityStage, LeaderboardEntry, Leaderboards, ParticipantRecord, ScoreTargets, SessionStatus } from '@/types/game'

const router = useRouter()
const { state } = useSession()
const activity = reactive<ActivitySnapshot>(demoActivity())
const participants = ref<ParticipantRecord[]>(demoParticipants())
const targets = reactive<ScoreTargets>(demoTargets())
const leaderboards = reactive<Leaderboards>(demoLeaderboards())
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const roundNumber = ref(1)
const groupNumber = ref(1)
const participantQuery = ref('')
const selectedMembers = ref<string[]>([])
const recommendations = ref<Array<{ id: string; participant_no: string; display_name: string; shared_count: number; never_shared: boolean }>>([])
const icebreakerWarnings = ref<Array<{ participant_id: string; shared_count: number }>>([])
const targetType = ref<'personal' | 'team' | 'college'>('personal')
const targetQuery = ref('')
const selectedTargetId = ref('')
const points = ref(0)
const scoreNote = ref('')
const leaderboardTab = ref<'personal' | 'team' | 'college'>('personal')
const identityLabel = computed(() => state.identity ? roleLabel(state.identity.role) : '活動展示工作台')
const isDemo = computed(() => !state.token || !state.identity)
const activeRoles = computed(() => state.identity?.available_roles?.length ? state.identity.available_roles : state.identity ? [state.identity.role] : [])
const currentStage = computed(() => activity.current_stage || activity.stages[0] || null)
const isScoringStage = computed(() => currentStage.value?.stage_type === 'score_only' || currentStage.value?.stage_type === 'mini_game' || currentStage.value?.stage_type === 'custom')
const canOperateIcebreaker = computed(() => isDemo.value || activeRoles.value.some((role) => role === 'coordinator' || role === 'icebreaker_facilitator' || role === 'team_facilitator'))
const canScore = computed(() => isDemo.value || activeRoles.value.some((role) => role === 'coordinator' || role === 'score_keeper' || role === 'team_facilitator'))
const status = computed<SessionStatus>(() => state.snapshot?.session.status || 'draft')
const period = computed(() => state.snapshot?.session.current_period || 0)
const navItems = computed(() => {
  if (state.identity?.role === 'coordinator') return [{ to: '/admin', label: '總覽', icon: 'dashboard' }, { to: '/admin/activity', label: '活動流程', icon: 'clock' }, { to: '/activity', label: '現場工作台', icon: 'spark' }]
  const items = [{ to: '/activity', label: '活動工作台', icon: 'spark' }]
  if (currentStage.value?.stage_type === 'magic_village') items.push({ to: '/user', label: '活米村', icon: 'map' })
  return items
})
const filteredParticipants = computed(() => {
  const query = participantQuery.value.toLowerCase()
  return participants.value.filter((person) => !query || `${person.participant_no} ${person.display_name}`.toLowerCase().includes(query))
})
const targetTabs = [{ value: 'personal', label: '個人' }, { value: 'team', label: '小隊' }, { value: 'college', label: '學院' }] as const
const leaderboardTabs = targetTabs
const filteredTargets = computed(() => {
  const query = targetQuery.value.toLowerCase()
  return targets[targetType.value].filter((target) => `${targetLabel(target)} ${targetMeta(target)} ${targetCode(target)}`.toLowerCase().includes(query))
})
const leaderboardEntries = computed<LeaderboardEntry[]>(() => leaderboards[leaderboardTab.value])
const leaderboardScope = computed(() => activity.current_stage ? `目前階段「${activity.current_stage.name}」；倍率：個人 ${activity.current_stage.personal_multiplier}・小隊 ${activity.current_stage.team_multiplier}・學院 ${activity.current_stage.college_multiplier}` : '所有已記錄分數')

onMounted(() => { void loadData() })

async function loadData() {
  if (isDemo.value || !state.token || !state.identity) return
  loading.value = true
  try {
    const activityData = await getActivity(state.identity.session_id, state.token)
    Object.assign(activity, activityData)
    const requests: Promise<unknown>[] = [getLeaderboards(state.identity.session_id, currentStage.value?.id || null, state.token)]
    if (activeRoles.value.some((role) => role === 'coordinator' || role === 'icebreaker_facilitator' || role === 'team_facilitator')) requests.push(getParticipants(state.identity.session_id, state.token))
    if (activeRoles.value.some((role) => role === 'coordinator' || role === 'score_keeper' || role === 'team_facilitator')) requests.push(getScoreTargets(state.identity.session_id, state.token))
    const results = await Promise.all(requests)
    const board = results[0] as Leaderboards
    Object.assign(leaderboards, board)
    let resultIndex = 1
    if (activeRoles.value.some((role) => role === 'coordinator' || role === 'icebreaker_facilitator' || role === 'team_facilitator')) { participants.value = results[resultIndex] as ParticipantRecord[]; resultIndex += 1 }
    if (activeRoles.value.some((role) => role === 'coordinator' || role === 'score_keeper' || role === 'team_facilitator')) Object.assign(targets, results[resultIndex] as ScoreTargets)
    if (currentStage.value?.stage_type === 'icebreaker') await loadRecommendations()
  } catch (error) { showError(error) } finally { loading.value = false }
}

async function loadRecommendations() {
  if (isDemo.value || !state.token || !currentStage.value || currentStage.value.stage_type !== 'icebreaker') return
  try { recommendations.value = await getIcebreakerRecommendations(currentStage.value.id, roundNumber.value, groupNumber.value, state.token) } catch (error) { showError(error) }
}

function addMember(id: string) { if (!selectedMembers.value.includes(id)) selectedMembers.value.push(id) }
function removeMember(id: string) { selectedMembers.value = selectedMembers.value.filter((memberId) => memberId !== id) }
async function saveGroup() {
  if (!currentStage.value || !selectedMembers.value.length || !state.token || !canOperateIcebreaker.value) return
  saving.value = true
  try { const result = await saveIcebreakerGroup({ stage_id: currentStage.value.id, round_number: roundNumber.value, group_number: groupNumber.value, participant_ids: selectedMembers.value }, state.token); icebreakerWarnings.value = result.warnings; showSuccess(`第 ${roundNumber.value} 輪第 ${groupNumber.value} 圈已記錄，共 ${result.members.length} 人。`); await loadRecommendations() } catch (error) { showError(error) } finally { saving.value = false }
}

async function submitScore() {
  if (!currentStage.value || !selectedTargetId.value || !state.token || !canScore.value) return
  saving.value = true
  try { const result = await recordScore({ stage_id: currentStage.value.id, target_type: targetType.value, target_id: selectedTargetId.value, points: Number(points.value), note: scoreNote.value || undefined, idempotency_key: createIdempotencyKey() }, state.token); showSuccess(result.replayed ? '這筆操作已經送出過，系統沒有重複加分。' : `已對${targetTypeLabel(targetType.value)}「${selectedTargetLabel.value}」記錄 ${points.value} 分。`); await refreshLeaderboard(); scoreNote.value = '' } catch (error) { showError(error) } finally { saving.value = false }
}

const selectedTargetLabel = computed(() => { const target = filteredTargets.value.find((item) => targetId(item) === selectedTargetId.value) || targets[targetType.value].find((item) => targetId(item) === selectedTargetId.value); return target ? targetLabel(target) : '目標' })
async function refreshLeaderboard() { if (state.token && state.identity) Object.assign(leaderboards, await getLeaderboards(state.identity.session_id, currentStage.value?.id || null, state.token)) }
function participantLabel(id: string) { const person = participants.value.find((item) => item.id === id); return person ? `${person.participant_no}・${person.display_name}` : '未知參加者' }
function targetId(target: ParticipantRecord | { id: string }) { return target.id }
function targetLabel(target: ParticipantRecord | { id: string; name?: string; display_name?: string }) { return 'display_name' in target ? target.display_name : target.name || '未命名目標' }
function targetMeta(target: ParticipantRecord | { id: string; number?: number; code?: string; name?: string; team_name?: string | null; college_name?: string | null }) { return 'participant_no' in target ? `${target.college_name || '未分院'}・${target.team_name || '未分隊'}` : 'number' in target ? `第 ${target.number} 隊` : `學院代碼 ${target.code || '—'}` }
function targetCode(target: ParticipantRecord | { id: string; number?: number; code?: string }) { return 'participant_no' in target ? target.participant_no : 'number' in target ? String(target.number) : target.code || '—' }
function entryCode(entry: LeaderboardEntry) { return entry.participant_no || (entry.number ? `第 ${entry.number} 隊` : entry.code || '') }
function targetTypeLabel(type: 'personal' | 'team' | 'college') { return type === 'personal' ? '個人' : type === 'team' ? '小隊' : '學院' }
function formatPoints(value: number) { return Number(value).toLocaleString('zh-TW', { maximumFractionDigits: 2 }) }
function createIdempotencyKey() { return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}` }
function stageDescription(type: ActivityStage['stage_type']) { return ({ icebreaker: '手機記錄圈圈成員，推薦尚未同圈的人。', score_only: '隊輔或記分員對指定目標快速加分。', mini_game: '小遊戲只記錄分數，不改變活米村資產。', magic_village: '沿用活米村市場、佔領與魔王規則。', custom: '依總召設定的自訂活動執行。' })[type] }
function showSuccess(text: string) { messageType.value = 'success'; message.value = text }
function showError(error: unknown) { messageType.value = 'error'; message.value = error instanceof ApiError ? error.message : error instanceof Error ? error.message : '操作失敗，請稍後再試。' }
function goLogin() { router.push('/login') }

function demoActivity(): ActivitySnapshot { return { current_stage: { id: 'demo-stage', name: '破冰', stage_type: 'icebreaker', sort_order: 1, start_offset_ms: 0, duration_minutes: 30, config: {}, personal_multiplier: 1, team_multiplier: 1, college_multiplier: 1 }, effective_elapsed_ms: 420000, active_roles: ['icebreaker_facilitator'], role: 'icebreaker_facilitator', stages: [{ id: 'demo-stage', name: '破冰', stage_type: 'icebreaker', sort_order: 1, start_offset_ms: 0, duration_minutes: 30, config: {}, personal_multiplier: 1, team_multiplier: 1, college_multiplier: 1 }] } }
function demoParticipants(): ParticipantRecord[] { return Array.from({ length: 12 }, (_, index) => ({ id: `demo-person-${index + 1}`, participant_no: `A${String(index + 1).padStart(3, '0')}`, display_name: `示範參加者 ${index + 1}`, email: `demo${index + 1}@example.com`, google_subject: false, college_id: null, college_code: null, college_name: `示範學院 ${(index % 3) + 1}`, team_id: null, team_number: (index % 4) + 1, team_name: `第 ${(index % 4) + 1} 隊`, active: true })) }
function demoTargets(): ScoreTargets { return { personal: demoParticipants(), team: Array.from({ length: 4 }, (_, index) => ({ id: `demo-team-${index + 1}`, number: index + 1, name: `第 ${index + 1} 隊` })), college: Array.from({ length: 3 }, (_, index) => ({ id: `demo-college-${index + 1}`, code: `C${index + 1}`, name: `示範學院 ${index + 1}` })) } }
function demoLeaderboards(): Leaderboards { return { stage_id: 'demo-stage', personal: [], team: [], college: [] } }
</script>

<style scoped>
.page-intro { display: flex; align-items: end; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
.page-intro h1 { margin-top: 4px; color: var(--color-ink); font-family: 'Noto Serif TC', Georgia, serif; font-size: clamp(25px, 4vw, 34px); }
.page-intro p { margin-top: 7px; color: var(--color-muted); font-size: 13px; line-height: 1.6; }
.eyebrow { color: var(--color-primary); font-size: 10px; font-weight: 900; letter-spacing: .14em; }
.stage-chip { display: grid; gap: 3px; min-width: 142px; padding: 11px 13px; color: var(--color-muted); background: var(--color-primary-soft); border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: 10px; }
.stage-chip strong { color: var(--color-primary-ink); font-size: 13px; }
.stage-chip small { font-size: 10px; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(310px, .95fr); gap: 16px; margin-top: 16px; }
.icebreaker-panel, .score-panel { min-width: 0; }
.leaderboard-panel { min-width: 0; }
.waiting-panel { grid-column: 1 / -1; }
.icebreaker-toolbar { display: grid; grid-template-columns: 1fr 1fr auto; align-items: end; gap: 9px; }
.search-field { display: flex; align-items: center; gap: 9px; min-height: 44px; margin-top: 13px; padding: 0 11px; background: var(--color-surface-raised); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); }
.search-field:focus-within { border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-soft); }
.search-field input { min-width: 0; flex: 1; color: var(--color-ink); background: transparent; border: 0; outline: none; font: inherit; font-size: 13px; }
.search-field small { color: var(--color-muted); font-size: 10px; white-space: nowrap; }
.selected-members { margin-top: 13px; padding: 11px; background: var(--color-primary-soft); border-radius: var(--radius-sm); }
.selected-members__head, .recommendation-box__head { display: flex; align-items: start; justify-content: space-between; gap: 10px; }
.selected-members strong, .recommendation-box strong { color: var(--color-primary-ink); font-size: 12px; }
.member-chip-list { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 9px; }
.member-chip { min-height: 31px; padding: 0 9px; color: var(--color-primary-ink); background: var(--color-surface); border: 1px solid var(--color-primary); border-radius: var(--radius-pill); font-size: 11px; font-weight: 800; }
.candidate-list, .target-list { display: grid; gap: 7px; max-height: 320px; margin-top: 13px; overflow-y: auto; overscroll-behavior: contain; }
.candidate-row, .target-row { display: grid; grid-template-columns: 31px minmax(0, 1fr) auto; align-items: center; gap: 9px; min-height: 53px; padding: 7px 9px; color: var(--color-ink); background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); text-align: left; }
.candidate-row:hover:not(:disabled), .target-row:hover, .target-row.is-selected { border-color: var(--color-primary); background: var(--color-primary-soft); }
.candidate-row:disabled { opacity: .58; }
.candidate-row strong, .candidate-row small, .target-row strong, .target-row small { display: block; }
.candidate-row strong, .target-row strong { font-size: 12px; }
.candidate-row small, .target-row small { margin-top: 3px; color: var(--color-muted); font-size: 10px; }
.candidate-state { color: var(--color-primary); font-size: 11px; font-weight: 800; }
.recommendation-box { margin-top: 14px; padding: 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.recommendation-box__head small { display: block; margin-top: 4px; color: var(--color-muted); font-size: 10px; }
.recommendation-box__head > span { color: var(--color-primary); font-size: 11px; font-weight: 800; }
.recommendation-row { display: grid; grid-template-columns: 48px minmax(0, 1fr) auto; gap: 8px; align-items: center; width: 100%; min-height: 35px; color: var(--color-ink); border-top: 1px solid var(--color-border); text-align: left; }
.recommendation-row:first-of-type { margin-top: 8px; }
.recommendation-row > span, .recommendation-row > small { color: var(--color-muted); font-size: 10px; }
.recommendation-row > strong { font-size: 11px; }
.warning-list { display: grid; gap: 5px; margin-top: 12px; padding: 10px; color: var(--color-accent); background: var(--color-warning-soft); border-radius: var(--radius-sm); font-size: 11px; }
.warning-list span { display: flex; align-items: start; gap: 6px; }
.warning-list .icon { flex: 0 0 auto; }
.primary-mobile-action { width: 100%; min-height: 48px; margin-top: 15px; }
.target-tabs, .leaderboard-tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 10px; }
.target-tabs button, .leaderboard-tabs button { min-height: 39px; color: var(--color-muted); background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: 12px; font-weight: 800; }
.target-tabs button.is-selected, .leaderboard-tabs button.is-selected { color: white; background: var(--color-primary); border-color: var(--color-primary); }
.target-row { grid-template-columns: 40px minmax(0, 1fr) 20px; }
.target-row.is-selected .target-key { color: white; background: var(--color-primary); }
.target-key { display: grid; width: 34px; height: 28px; place-items: center; color: var(--color-primary-ink); background: var(--color-primary-soft); border-radius: var(--radius-sm); font-size: 11px; font-weight: 900; }
.score-entry { display: grid; grid-template-columns: .55fr 1.45fr; gap: 9px; margin-top: 13px; }
.leaderboard-list { display: grid; gap: 7px; }
.leaderboard-row { display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; align-items: center; gap: 9px; min-height: 52px; padding: 7px 9px; background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.rank-number { color: var(--color-primary); font-size: 13px; font-weight: 900; text-align: center; }
.leaderboard-name strong, .leaderboard-name small, .score-values strong, .score-values small { display: block; }
.leaderboard-name strong { color: var(--color-ink); font-size: 12px; }
.leaderboard-name small, .score-values small { margin-top: 3px; color: var(--color-muted); font-size: 10px; }
.score-values { text-align: right; }
.score-values strong { color: var(--color-primary-ink); font-size: 15px; font-variant-numeric: tabular-nums; }
.empty-state { padding: 16px; color: var(--color-muted); background: var(--color-surface-raised); border-radius: var(--radius-sm); font-size: 12px; text-align: center; }
.sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
@media (max-width: 900px) { .workspace-grid { grid-template-columns: 1fr; } .waiting-panel { grid-column: auto; } }
@media (max-width: 560px) { .page-intro { align-items: flex-start; flex-direction: column; } .stage-chip { width: 100%; } .icebreaker-toolbar { grid-template-columns: 1fr 1fr; } .icebreaker-toolbar .ghost-button { grid-column: 1 / -1; width: 100%; } .score-entry { grid-template-columns: 1fr; } .candidate-list, .target-list { max-height: 280px; } }
</style>
