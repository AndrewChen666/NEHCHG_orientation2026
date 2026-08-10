<template>
  <GameShell
    role-label="總召控制台"
    identity="活動流程與現場身分"
    :nav-items="navItems"
    :hide-page-heading="true"
    :connected="!isDemo"
    :demo="isDemo"
    :period="period"
    :elapsed-ms="elapsedMs"
    :status="status"
    :money="0"
    @sign-out="goLogin"
  >
    <template #heading-actions>
      <button class="ghost-button" type="button" :disabled="loading" @click="loadData"><Icon name="clock" size="sm" />重新讀取</button>
      <button class="action-button" type="button" :disabled="isDemo || saving" :class="{ 'is-loading': saving }" @click="saveAll"><Icon name="check" size="sm" />{{ saving ? '儲存中…' : '儲存活動設定' }}</button>
    </template>

    <div class="page-intro">
      <div><span class="eyebrow">ORIENTATION 2026</span><h1>活動流程</h1><p>把整天拆成可排序的階段；參加者在不同階段可以擁有不同現場身分。</p></div>
      <span class="status-badge" :class="isDemo ? 'is-neutral' : 'is-success'">{{ isDemo ? '展示資料' : `${stages.length} 個階段` }}</span>
    </div>

    <div class="notice"><Icon name="alert" size="sm" /><span>階段與身分在場次開始後鎖定。活動開始時以伺服器時間判定目前階段，總召也可以在現場手動切換。</span></div>
    <div v-if="message" class="form-message" :class="{ 'is-error': messageType === 'error' }"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</div>

    <div class="setup-grid">
      <section class="section-block">
        <div class="section-block__head"><div><h2>1. 活動階段</h2><p>順序、時間與三套獨立倍率</p></div><button class="ghost-button" type="button" :disabled="isLocked" @click="addStage"><Icon name="spark" size="sm" />新增階段</button></div>
        <div class="stage-list">
          <article v-for="(stage, index) in stages" :key="stage.id" class="stage-card" :class="{ 'is-current': activity.current_stage?.id === stage.id }">
            <div class="stage-card__top"><span class="stage-number">{{ index + 1 }}</span><div class="stage-card__title"><input v-model.trim="stage.name" class="stage-name" type="text" maxlength="80" aria-label="階段名稱" /><span v-if="activity.current_stage?.id === stage.id" class="status-badge is-success">目前階段</span></div><button class="icon-button" type="button" title="刪除階段" :disabled="isLocked || stages.length <= 1" @click="removeStage(stage.id)">×</button></div>
            <div class="form-grid stage-fields">
              <label class="form-field"><span>類型</span><select v-model="stage.stage_type"><option value="icebreaker">破冰</option><option value="score_only">純計分</option><option value="mini_game">小遊戲</option><option value="magic_village">活米村</option><option value="custom">自訂活動</option></select></label>
              <label class="form-field"><span>開始（活動後分鐘）</span><input :value="stageStartMinutes[index]" type="number" min="0" max="100000" inputmode="numeric" @change="setStartMinutes(stage, $event)" /></label>
              <label class="form-field"><span>持續分鐘</span><input v-model.number="stage.duration_minutes" type="number" min="1" max="1440" inputmode="numeric" /></label>
            </div>
            <div class="multiplier-row"><span>總分倍率</span><label><small>個人</small><input v-model.number="stage.personal_multiplier" type="number" min="0" step="0.1" inputmode="decimal" /></label><label><small>小隊</small><input v-model.number="stage.team_multiplier" type="number" min="0" step="0.1" inputmode="decimal" /></label><label><small>學院</small><input v-model.number="stage.college_multiplier" type="number" min="0" step="0.1" inputmode="decimal" /></label></div>
            <div v-if="isCoordinator" class="stage-actions"><button class="text-button" type="button" :disabled="isDemo || isLocked || !isPersistedStage(stage)" @click="activateStage(stage)">{{ activity.current_stage?.id === stage.id ? '目前正在使用' : '手動切換到這一階段' }}</button><span>{{ stageTypeLabel(stage.stage_type) }}</span></div>
          </article>
        </div>
      </section>

      <section class="section-block">
        <div class="section-block__head"><div><h2>2. 參加者名單</h2><p>Google email 是登入白名單；可用 CSV 一次匯入。</p></div><span class="status-badge is-neutral">{{ participants.length }} 人</span></div>
        <label class="file-picker"><span>選擇 CSV</span><input ref="csvFile" type="file" accept=".csv,text/csv" @change="readCsvFile" /></label>
        <label class="form-field"><span>CSV 內容</span><textarea v-model="csvText" rows="7" placeholder="編號,姓名,email,學院,小隊&#10;A001,王小明,person@example.com,獅院,1"></textarea></label>
        <div class="csv-help">欄位支援：編號、姓名、email、學院代碼／學院、小隊。重複編號、重複 email、未知小隊會整批拒絕。</div>
        <button class="action-button full-button" type="button" :disabled="isDemo || importing || !csvText.trim()" :class="{ 'is-loading': importing }" @click="importRoster">{{ importing ? '匯入中…' : '匯入參加者名單' }}</button>
        <div class="participant-preview" aria-label="已匯入參加者"><div v-for="person in participants.slice(0, 8)" :key="person.id" class="person-row"><span class="participant-number">{{ person.participant_no }}</span><span><strong>{{ person.display_name }}</strong><small>{{ person.email }}</small></span><span class="person-team">{{ person.college_name || '未分院' }}・{{ person.team_name || '未分隊' }}</span></div><p v-if="participants.length > 8" class="csv-help">還有 {{ participants.length - 8 }} 位參加者未顯示。</p></div>
      </section>

      <section class="section-block assignment-section">
        <div class="section-block__head"><div><h2>3. 階段身分</h2><p>同一人可以在不同階段擁有不同身分；範圍可限制到學院或小隊。</p></div><span class="status-badge is-neutral">{{ assignments.length }} 筆</span></div>
        <div class="assignment-form">
          <label class="form-field"><span>階段</span><select v-model="assignmentDraft.stage_id"><option value="" disabled>選擇階段</option><option v-for="stage in persistedStages" :key="stage.id" :value="stage.id">{{ stage.name }}</option></select></label>
          <label class="form-field"><span>參加者</span><select v-model="assignmentDraft.participant_id"><option value="" disabled>選擇參加者</option><option v-for="person in participants" :key="person.id" :value="person.id">{{ person.participant_no }}・{{ person.display_name }}</option></select></label>
          <label class="form-field"><span>身分</span><select v-model="assignmentDraft.role"><option v-for="role in roleOptions" :key="role.value" :value="role.value">{{ role.label }}</option></select></label>
          <label class="form-field"><span>範圍</span><select v-model="assignmentDraft.scope_type"><option value="session">整場</option><option value="college">學院</option><option value="team">小隊</option></select></label>
          <button class="ghost-button assignment-add" type="button" :disabled="!assignmentDraft.stage_id || !assignmentDraft.participant_id" @click="addAssignment">加入指派</button>
        </div>
        <div class="assignment-list"><div v-for="(assignment, index) in assignments" :key="assignment.id || `${assignment.stage_id}-${assignment.participant_id}-${assignment.role}-${index}`" class="assignment-row"><div><strong>{{ assignment.display_name || participantName(assignment.participant_id) }}</strong><small>{{ assignment.stage_name || stageName(assignment.stage_id) }}・{{ roleLabel(assignment.role) }}・{{ scopeLabel(assignment) }}</small></div><button class="icon-button" type="button" :disabled="isLocked" title="移除指派" @click="assignments.splice(index, 1)">×</button></div><p v-if="!assignments.length" class="empty-state">還沒有階段身分指派。</p></div>
        <button class="action-button full-button" type="button" :disabled="isDemo || saving || isLocked" @click="saveAssignments">儲存階段身分</button>
      </section>
    </div>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, getActivity, getActivityStages, getParticipants, getRoleAssignments, importParticipants, setActiveStage, updateActivityStages, updateRoleAssignments } from '@/lib/api'
import { useSession } from '@/lib/session'
import type { AccessIdentity, ActivitySnapshot, ActivityStage, ActivityStageType, ParticipantRecord, Role, RoleAssignmentRecord, SessionStatus } from '@/types/game'

const router = useRouter()
const { state } = useSession()
const navItems = [{ to: '/admin', label: '總覽', icon: 'dashboard' }, { to: '/admin/activity', label: '活動流程', icon: 'clock' }, { to: '/admin/setup', label: '開局設定', icon: 'spark' }, { to: '/admin/markets', label: '市場與行情', icon: 'market' }, { to: '/admin/teams', label: '隊伍資產', icon: 'team' }, { to: '/admin/map', label: '地圖與佔領', icon: 'map' }]
const activity = reactive<ActivitySnapshot>(demoActivity())
const stages = ref<ActivityStage[]>(activity.stages)
const participants = ref<ParticipantRecord[]>(demoParticipants())
const assignments = ref<RoleAssignmentRecord[]>([])
const csvText = ref('')
const csvFile = ref<HTMLInputElement | null>(null)
const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const assignmentDraft = reactive<{ stage_id: string; participant_id: string; role: Role; scope_type: 'session' | 'college' | 'team' }>({ stage_id: '', participant_id: '', role: 'icebreaker_facilitator', scope_type: 'session' })
const roleOptions: Array<{ value: Role; label: string }> = [
  { value: 'participant', label: '參加者' }, { value: 'team_facilitator', label: '隊輔' }, { value: 'icebreaker_facilitator', label: '破冰隊輔' }, { value: 'score_keeper', label: '記分員' }, { value: 'market_master', label: '關主' }, { value: 'magic_boss', label: '魔王' },
]
const isDemo = computed(() => !state.token || state.identity?.role !== 'coordinator')
const isCoordinator = computed(() => state.identity?.role === 'coordinator')
const status = computed<SessionStatus>(() => state.snapshot?.session.status || 'draft')
const period = computed(() => state.snapshot?.session.current_period || 0)
const elapsedMs = computed(() => activity.effective_elapsed_ms)
const isLocked = computed(() => status.value === 'running' || status.value === 'paused' || status.value === 'finished')
const persistedStages = computed(() => stages.value.filter(isPersistedStage))
const stageStartMinutes = computed(() => stages.value.map((stage) => Math.round(stage.start_offset_ms / 60000)))

onMounted(() => { void loadData() })

async function loadData() {
  if (isDemo.value || !state.token || !state.identity) return
  loading.value = true
  try {
    const [activityData, stageData, participantData, assignmentData] = await Promise.all([
      getActivity(state.identity.session_id, state.token), getActivityStages(state.identity.session_id, state.token), getParticipants(state.identity.session_id, state.token), getRoleAssignments(state.identity.session_id, state.token),
    ])
    Object.assign(activity, activityData)
    stages.value = stageData
    participants.value = participantData
    assignments.value = assignmentData
    if (!assignmentDraft.stage_id) assignmentDraft.stage_id = persistedStages.value[0]?.id || ''
  } catch (error) { showError(error) } finally { loading.value = false }
}

function addStage() {
  const last = stages.value[stages.value.length - 1]
  stages.value.push({ id: `draft-${Date.now()}`, name: '新活動階段', stage_type: 'custom', sort_order: stages.value.length + 1, start_offset_ms: last ? last.start_offset_ms + last.duration_minutes * 60000 : 0, duration_minutes: 30, config: {}, personal_multiplier: 1, team_multiplier: 1, college_multiplier: 1 })
}

function removeStage(stageId: string) {
  stages.value = stages.value.filter((stage) => stage.id !== stageId)
  assignments.value = assignments.value.filter((assignment) => assignment.stage_id !== stageId)
}

function setStartMinutes(stage: ActivityStage, event: Event) { stage.start_offset_ms = Math.max(0, Number((event.target as HTMLInputElement).value) || 0) * 60000 }

function isPersistedStage(stage: ActivityStage) { return !stage.id.startsWith('draft-') }

async function saveAll() {
  await saveStages()
  if (!isDemo.value && assignments.value.length) await saveAssignments()
}

async function saveStages() {
  if (isDemo.value || !state.token || !state.identity || isLocked.value) return
  saving.value = true
  try {
    stages.value.forEach((stage, index) => { stage.sort_order = index + 1; stage.name = stage.name.trim() || `活動階段 ${index + 1}` })
    const payload = stages.value.map((stage) => { const { id, ...body } = stage; return isPersistedStage(stage) ? { id, ...body } : body }) as ActivityStage[]
    await updateActivityStages(state.identity.session_id, payload, state.token)
    await loadData()
    showSuccess('活動階段已儲存。')
  } catch (error) { showError(error) } finally { saving.value = false }
}

async function activateStage(stage: ActivityStage) {
  if (isDemo.value || !state.token || !state.identity || !isPersistedStage(stage)) return
  try { await setActiveStage(state.identity.session_id, stage.id, state.token); activity.current_stage = stage; showSuccess(`已手動切換到「${stage.name}」。`) } catch (error) { showError(error) }
}

async function readCsvFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) csvText.value = await file.text()
}

async function importRoster() {
  if (isDemo.value || !state.token || !state.identity) return
  importing.value = true
  try { const result = await importParticipants(state.identity.session_id, csvText.value, state.token); await loadData(); showSuccess(`名單匯入完成：新增 ${result.created} 人、更新 ${result.updated} 人。`); if (csvFile.value) csvFile.value.value = '' } catch (error) { showError(error) } finally { importing.value = false }
}

function addAssignment() {
  const person = participants.value.find((item) => item.id === assignmentDraft.participant_id)
  if (!person || assignments.value.some((item) => item.stage_id === assignmentDraft.stage_id && item.participant_id === assignmentDraft.participant_id && item.role === assignmentDraft.role && item.scope_type === assignmentDraft.scope_type)) return
  assignments.value.push({ stage_id: assignmentDraft.stage_id, participant_id: assignmentDraft.participant_id, role: assignmentDraft.role, scope_type: assignmentDraft.scope_type, college_id: assignmentDraft.scope_type === 'college' ? person.college_id : null, team_id: assignmentDraft.scope_type === 'team' ? person.team_id : null, display_name: person.display_name, participant_no: person.participant_no, stage_name: stageName(assignmentDraft.stage_id), active: true })
}

async function saveAssignments() {
  if (isDemo.value || !state.token || !state.identity || isLocked.value) return
  saving.value = true
  try { const payload = assignments.value.map(({ id: _id, stage_name: _stageName, display_name: _displayName, participant_no: _participantNo, ...assignment }) => assignment); await updateRoleAssignments(state.identity.session_id, payload, state.token); await loadData(); showSuccess('階段身分已儲存。') } catch (error) { showError(error) } finally { saving.value = false }
}

function participantName(id: string) { return participants.value.find((person) => person.id === id)?.display_name || '未指定參加者' }
function stageName(id: string) { return stages.value.find((stage) => stage.id === id)?.name || '未指定階段' }
function roleLabel(role: Role) { return roleOptions.find((item) => item.value === role)?.label || role }
function scopeLabel(assignment: RoleAssignmentRecord) { return assignment.scope_type === 'team' ? '小隊範圍' : assignment.scope_type === 'college' ? '學院範圍' : '整場' }
function stageTypeLabel(type: ActivityStageType) { return ({ icebreaker: '破冰工作台', score_only: '純計分', mini_game: '小遊戲', magic_village: '活米村', custom: '自訂活動' })[type] }
function showSuccess(text: string) { messageType.value = 'success'; message.value = text }
function showError(error: unknown) { messageType.value = 'error'; message.value = error instanceof ApiError ? error.message : error instanceof Error ? error.message : '操作失敗，請稍後再試。' }
function goLogin() { router.push('/login') }

function demoActivity(): ActivitySnapshot { return { current_stage: null, effective_elapsed_ms: 0, active_roles: ['coordinator'], role: 'coordinator', stages: [{ id: 'demo-icebreaker', name: '破冰', stage_type: 'icebreaker', sort_order: 1, start_offset_ms: 0, duration_minutes: 30, config: {}, personal_multiplier: 1, team_multiplier: 1, college_multiplier: 1 }, { id: 'demo-score', name: '小遊戲計分', stage_type: 'score_only', sort_order: 2, start_offset_ms: 1800000, duration_minutes: 45, config: {}, personal_multiplier: 1, team_multiplier: 1, college_multiplier: 1 }, { id: 'demo-village', name: '活米村', stage_type: 'magic_village', sort_order: 3, start_offset_ms: 4500000, duration_minutes: 240, config: {}, personal_multiplier: 0, team_multiplier: 1, college_multiplier: 1 }] } }
function demoParticipants(): ParticipantRecord[] { return Array.from({ length: 6 }, (_, index) => ({ id: `demo-person-${index + 1}`, participant_no: `A${String(index + 1).padStart(3, '0')}`, display_name: ['王小明', '林佳蓉', '陳柏宇', '李欣怡', '張庭安', '吳承翰'][index] || `示範參加者 ${index + 1}`, email: `demo${index + 1}@example.com`, google_subject: false, college_id: null, college_code: null, college_name: `示範學院 ${index % 2 + 1}`, team_id: null, team_number: index % 3 + 1, team_name: `示範小隊 ${index % 3 + 1}`, active: true })) }
</script>

<style scoped>
.page-intro { display: flex; align-items: end; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
.page-intro h1 { margin-top: 4px; color: var(--color-ink); font-family: 'Noto Serif TC', Georgia, serif; font-size: clamp(25px, 4vw, 34px); }
.page-intro p { margin-top: 7px; color: var(--color-muted); font-size: 13px; line-height: 1.6; }
.eyebrow { color: var(--color-primary); font-size: 10px; font-weight: 900; letter-spacing: .14em; }
.setup-grid { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(280px, .8fr); gap: 16px; margin-top: 16px; }
.assignment-section { grid-column: 1 / -1; }
.stage-list, .assignment-list, .participant-preview { display: grid; gap: 10px; }
.stage-card { display: grid; gap: 13px; padding: 14px; background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.stage-card.is-current { border-color: var(--color-primary); box-shadow: 0 0 0 2px var(--color-primary-soft); }
.stage-card__top, .stage-card__title, .stage-actions, .assignment-row, .multiplier-row { display: flex; align-items: center; gap: 9px; }
.stage-card__top { justify-content: space-between; }
.stage-card__title { flex: 1; min-width: 0; flex-wrap: wrap; }
.stage-number, .participant-number { display: grid; flex: 0 0 auto; width: 29px; height: 29px; place-items: center; color: var(--color-primary-ink); background: var(--color-primary-soft); border-radius: 50%; font-size: 12px; font-weight: 900; }
.stage-name { min-width: 120px; flex: 1; min-height: 34px; padding: 0 8px; color: var(--color-ink); background: transparent; border: 0; border-bottom: 1px solid var(--color-border-strong); font-size: 14px; font-weight: 900; outline: none; }
.stage-name:focus { border-color: var(--color-primary); }
.stage-fields { grid-template-columns: 1.1fr 1fr 1fr; gap: 9px; }
.multiplier-row { padding-top: 11px; border-top: 1px solid var(--color-border); color: var(--color-muted); font-size: 11px; }
.multiplier-row > span { margin-right: auto; font-weight: 800; }
.multiplier-row label { display: grid; grid-template-columns: auto 55px; align-items: center; gap: 5px; }
.multiplier-row input { width: 55px; min-height: 30px; padding: 0 5px; color: var(--color-ink); background: var(--color-surface); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); text-align: right; }
.multiplier-row small { font-size: 10px; }
.stage-actions { justify-content: space-between; color: var(--color-muted); font-size: 11px; }
.icon-button { display: inline-grid; width: 34px; height: 34px; place-items: center; color: var(--color-muted); background: transparent; border: 1px solid var(--color-border); border-radius: 50%; font-size: 18px; }
.icon-button:hover:not(:disabled) { color: var(--color-danger); border-color: var(--color-danger); }
.icon-button:disabled { opacity: .45; }
.file-picker { display: inline-flex; align-items: center; min-height: 39px; margin-bottom: 12px; padding: 0 13px; color: var(--color-primary-ink); background: var(--color-primary-soft); border: 1px dashed var(--color-primary); border-radius: var(--radius-sm); font-size: 12px; font-weight: 800; cursor: pointer; }
.file-picker input { display: none; }
.form-field textarea { width: 100%; padding: 10px 11px; color: var(--color-ink); background: var(--color-surface); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); outline: none; font: inherit; font-size: 12px; line-height: 1.5; resize: vertical; }
.form-field textarea:focus { border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-soft); }
.csv-help { color: var(--color-muted); font-size: 11px; line-height: 1.55; }
.full-button { width: 100%; margin-top: 12px; }
.participant-preview { margin-top: 15px; padding-top: 12px; border-top: 1px solid var(--color-border); }
.person-row { display: grid; grid-template-columns: 31px minmax(0, 1fr) auto; align-items: center; gap: 9px; min-width: 0; }
.person-row strong, .person-row small { display: block; }
.person-row strong { color: var(--color-ink); font-size: 12px; }
.person-row small, .person-team { overflow: hidden; color: var(--color-muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.person-team { max-width: 130px; }
.assignment-form { display: grid; grid-template-columns: 1fr 1.2fr 1fr .8fr auto; align-items: end; gap: 9px; }
.assignment-add { min-height: 41px; }
.assignment-row { justify-content: space-between; padding: 10px 11px; background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.assignment-row strong, .assignment-row small { display: block; }
.assignment-row strong { color: var(--color-ink); font-size: 12px; }
.assignment-row small { margin-top: 3px; color: var(--color-muted); font-size: 10px; }
.empty-state { padding: 16px; color: var(--color-muted); background: var(--color-surface-raised); border-radius: var(--radius-sm); font-size: 12px; text-align: center; }
@media (max-width: 900px) { .setup-grid { grid-template-columns: 1fr; } .assignment-section { grid-column: auto; } }
@media (max-width: 680px) { .page-intro { align-items: flex-start; flex-direction: column; } .stage-fields, .assignment-form { grid-template-columns: 1fr 1fr; } .assignment-add { grid-column: 1 / -1; } .multiplier-row { align-items: start; flex-wrap: wrap; } .multiplier-row > span { width: 100%; } .person-row { grid-template-columns: 31px minmax(0, 1fr); } .person-team { grid-column: 2; max-width: none; } }
@media (max-width: 440px) { .stage-fields, .assignment-form { grid-template-columns: 1fr; } .multiplier-row label { flex: 1; } .multiplier-row label input { width: 100%; } }
</style>
