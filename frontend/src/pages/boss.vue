<template>
  <GameShell
    role-label="隱藏魔王"
    :identity="state.identity?.display_name || '隱藏魔王'"
    hide-page-heading
    :nav-items="navItems"
    :connected="!isDemo"
    :demo="isDemo"
    :period="snapshot.session.current_period"
    :elapsed-ms="snapshot.session.effective_elapsed_ms"
    :status="snapshot.session.status"
    :money="0"
    @sign-out="goLogin"
  >
    <template #heading-actions>
      <button class="ghost-button" :class="{ 'is-loading': loading }" type="button" :disabled="loading" :aria-busy="loading" @click="loadBossDesk"><Icon name="clock" size="sm" />重新整理</button>
    </template>

    <div class="field-board boss-board">
      <section class="board-panel boss-create">
        <div class="board-panel__head"><div><span class="step-label">登記新挑戰</span><h2>隊伍到場了？</h2><p>選隊伍與題目後，按一次即可開始記錄。</p></div><span class="status-badge is-warning">魔王專用</span></div>

        <div class="form-grid two-up">
          <label class="form-field"><span>到場隊伍</span><select v-model="selectedTeamId"><option value="" disabled>選擇隊伍</option><option v-for="team in snapshot.teams" :key="team.id" :value="team.id">第 {{ team.number }} 隊・{{ team.name }}</option></select></label>
          <label class="form-field"><span>現場題目</span><select v-model="selectedQuestionId"><option value="" disabled>選擇題目</option><option v-for="question in questions" :key="question.id" :value="question.id">{{ question.subject }}・難度 {{ roman(question.difficulty_level) }}</option></select></label>
        </div>

        <div v-if="selectedQuestion" class="question-strip">
          <div><strong>{{ selectedQuestion.subject }}</strong><span>難度 {{ roman(selectedQuestion.difficulty_level) }}</span></div>
          <b>成功 +{{ selectedQuestion.reward }}</b>
          <details v-if="selectedQuestion.prompt || selectedQuestion.answer_note"><summary>看題目備忘</summary><p>{{ selectedQuestion.prompt || '依現場題卡提問。' }}<br v-if="selectedQuestion.answer_note" /><small v-if="selectedQuestion.answer_note">答案：{{ selectedQuestion.answer_note }}</small></p></details>
        </div>
        <div v-else class="board-hint"><Icon name="alert" size="sm" />請先選擇隊伍與題目。</div>

        <div class="check-grid compact-checks">
          <label v-if="rules.guard_money_pouch" class="check-row"><input v-model="guards.money" type="checkbox" /><span>金錢袋已出示</span></label>
          <label v-if="rules.guard_minimum_team_present" class="check-row"><input v-model="guards.team" type="checkbox" /><span>至少半數隊員在場</span></label>
        </div>
        <button class="action-button board-primary-action" :class="{ 'is-loading': submitting }" type="button" :disabled="!canCreate || submitting" :aria-busy="submitting" @click="recordEncounter">{{ submitting ? '記錄中…' : '記錄現場挑戰' }}<Icon name="spark" size="sm" /></button>
      </section>

      <section class="board-panel boss-pending">
        <div class="board-panel__head"><div><span class="step-label">現在要處理</span><h2>進行中的挑戰</h2></div><span class="status-badge" :class="pending.length ? 'is-warning' : 'is-success'">{{ pending.length }} 筆</span></div>
        <div v-if="pending.length" class="fast-list">
          <article v-for="challenge in pending" :key="challenge.id" class="fast-item">
            <div class="fast-item__main"><span class="team-badge">{{ challenge.team_number }}</span><div><strong>第 {{ challenge.team_number }} 隊・{{ challenge.team_name }}</strong><span>{{ challenge.subject }}・難度 {{ roman(challenge.difficulty_level) }}・成功 +{{ challenge.reward }}</span></div></div>
            <details v-if="challenge.prompt || challenge.answer_note" class="fast-details"><summary>題目備忘</summary><p>{{ challenge.prompt }}<br v-if="challenge.answer_note" /><small v-if="challenge.answer_note">答案：{{ challenge.answer_note }}</small></p></details>
            <input v-model="notes[challenge.id]" class="fast-note" type="text" maxlength="500" placeholder="備註（選填）" />
            <div class="fast-actions"><button class="action-button" :class="{ 'is-loading': submitting }" type="button" :disabled="submitting" :aria-busy="submitting" @click="finishEncounter(challenge, true)"><Icon name="check" size="sm" />成功 +{{ challenge.reward }}</button><button class="ghost-button is-danger" :class="{ 'is-loading': submitting }" type="button" :disabled="submitting" :aria-busy="submitting" @click="finishEncounter(challenge, false)">失敗</button></div>
          </article>
        </div>
        <div v-else class="board-empty"><Icon name="check" size="md" /><strong>沒有待結束挑戰</strong><span>下一隊到場時，從左側登記。</span></div>
      </section>

      <section class="board-panel boss-history">
        <div class="board-panel__head"><div><h2>最近判定</h2><p>成功與失敗都會留痕</p></div><span class="mini-label">{{ history.length }} 筆</span></div>
        <div v-if="history.length" class="history-strip"><div v-for="item in history.slice(0, 4)" :key="item.id" class="history-chip"><span class="team-badge">{{ item.team_number }}</span><span>第 {{ item.team_number }} 隊・{{ item.subject }}</span><b :class="item.result === 'success' ? 'is-success' : 'is-failed'">{{ item.result === 'success' ? `+${item.reward}` : '失敗' }}</b></div></div>
        <p v-else class="mini-label">完成第一場挑戰後，結果會出現在這裡。</p>
      </section>
      <p v-if="message" class="board-message" :class="{ 'is-error': messageType === 'error' }" aria-live="polite"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</p>
    </div>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, createMagicChallenge, getGameConfig, getMagicChallengeHistory, getMagicQuestions, getPendingMagicChallenges, getSnapshot, gradeMagicChallenge } from '@/lib/api'
import { cloneDefaultConfig } from '@/lib/gameConfig'
import { useSession } from '@/lib/session'
import type { GameConfig, GameSnapshot, MagicChallengeHistory, MagicQuestion, PendingMagicChallenge } from '@/types/game'

const router = useRouter()
const { state } = useSession()
const navItems = [{ to: '/boss', label: '魔王工作板', icon: 'spark' }]
const snapshot = reactive<GameSnapshot>(demoSnapshot())
const config = reactive<GameConfig>(cloneDefaultConfig())
const questions = ref<MagicQuestion[]>(demoQuestions())
const pending = ref<PendingMagicChallenge[]>(demoPending())
const history = ref<MagicChallengeHistory[]>(demoHistory())
const selectedTeamId = ref('demo-team-1')
const selectedQuestionId = ref(questions.value[0]?.id || '')
const notes = reactive<Record<string, string>>({})
const guards = reactive({ money: false, team: false })
const loading = ref(false)
const submitting = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const isDemo = computed(() => !state.token || state.identity?.role !== 'magic_boss')
const rules = computed(() => config.rules)
const selectedQuestion = computed(() => questions.value.find((question) => question.id === selectedQuestionId.value))
const canCreate = computed(() => Boolean(selectedTeamId.value && selectedQuestion.value && (!rules.value.guard_money_pouch || guards.money) && (!rules.value.guard_minimum_team_present || guards.team)))

onMounted(loadBossDesk)

async function loadBossDesk() {
  if (isDemo.value || !state.identity || !state.token) return
  loading.value = true
  try {
    const [nextSnapshot, nextConfig, nextQuestions, nextPending, nextHistory] = await Promise.all([
      getSnapshot(state.identity.session_id, state.token), getGameConfig(state.identity.session_id, state.token), getMagicQuestions(state.identity.session_id, state.token), getPendingMagicChallenges(state.identity.session_id, state.token), getMagicChallengeHistory(state.identity.session_id, state.token),
    ])
    Object.assign(snapshot, nextSnapshot); Object.assign(config, nextConfig); questions.value = nextQuestions; pending.value = nextPending; history.value = nextHistory
    selectedTeamId.value = snapshot.teams[0]?.id || ''; selectedQuestionId.value = questions.value[0]?.id || ''
  } catch (error) { showError(error) } finally { loading.value = false }
}

async function recordEncounter() {
  if (!selectedQuestion.value || !selectedTeamId.value || !canCreate.value) return
  submitting.value = true
  try {
    if (isDemo.value) {
      const team = snapshot.teams.find((item) => item.id === selectedTeamId.value)
      pending.value.unshift({ id: `demo-pending-${Date.now()}`, team_id: selectedTeamId.value, team_number: team?.number || 1, team_name: team?.name || '展示隊伍', subject: selectedQuestion.value.subject, difficulty_level: selectedQuestion.value.difficulty_level, prompt: selectedQuestion.value.prompt || '現場題目', answer_note: selectedQuestion.value.answer_note, reward: selectedQuestion.value.reward, created_at: new Date().toISOString() })
      messageType.value = 'success'; message.value = '已登記，完成現場挑戰後在右側按結果。'
    } else if (state.token) {
      await createMagicChallenge({ team_id: selectedTeamId.value, question_id: selectedQuestion.value.id, money_pouch_presented: guards.money, minimum_team_present: guards.team, idempotency_key: requestId() }, state.token)
      await loadBossDesk(); messageType.value = 'success'; message.value = '挑戰已登記，完成後再判定結果。'
    }
    guards.money = false; guards.team = false
  } catch (error) { showError(error) } finally { submitting.value = false }
}

async function finishEncounter(challenge: PendingMagicChallenge, success: boolean) {
  submitting.value = true
  try {
    if (isDemo.value) {
      pending.value = pending.value.filter((item) => item.id !== challenge.id); history.value.unshift({ ...challenge, result: success ? 'success' : 'failed', note: notes[challenge.id] || null, judged_at: new Date().toISOString() }); messageType.value = 'success'; message.value = success ? `已展示派發 ${challenge.reward} 枚金幣。` : '已展示新增挑戰失敗紀錄。'
    } else if (state.token) {
      const result = await gradeMagicChallenge(challenge.id, success, notes[challenge.id], state.token); await loadBossDesk(); messageType.value = 'success'; message.value = success ? `判定成功，已派發 ${result.reward} 枚金幣。` : '判定失敗，挑戰紀錄已保存。'
    }
  } catch (error) { showError(error) } finally { submitting.value = false }
}

function roman(level: number) { return ['I', 'II', 'III', 'IV', 'V'][level - 1] || level }
function requestId() { return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `magic-${Date.now()}` }
function showError(error: unknown) { messageType.value = 'error'; message.value = error instanceof ApiError ? error.message : error instanceof Error ? error.message : '目前無法完成魔王操作。' }
function goLogin() { router.push('/login') }
function demoQuestions(): MagicQuestion[] { return [{ id: 'demo-question-1', subject: '自然科', difficulty_level: 3, reward: 5, prompt: '由魔王在現場口頭提出題目。', answer_note: '展示答案備忘：依現場題卡判定。' }, { id: 'demo-question-2', subject: '資訊', difficulty_level: 4, reward: 10, prompt: '由魔王在現場口頭提出題目。', answer_note: '展示答案備忘：依現場題卡判定。' }] }
function demoPending(): PendingMagicChallenge[] { return [{ id: 'demo-pending-1', team_id: 'demo-team-2', team_number: 2, team_name: '2', subject: '自然科', difficulty_level: 3, prompt: '由魔王在現場口頭提出題目。', answer_note: '展示答案備忘：依現場題卡判定。', reward: 5, created_at: new Date().toISOString() }] }
function demoHistory(): MagicChallengeHistory[] { return [{ id: 'demo-history-1', team_id: 'demo-team-7', team_number: 7, team_name: '7', subject: '資訊', difficulty_level: 2, prompt: '現場題目', reward: 3, result: 'failed', note: '未完成指定條件', judged_at: new Date(Date.now() - 3600000).toISOString(), created_at: new Date(Date.now() - 4200000).toISOString() }] }
function demoSnapshot(): GameSnapshot { return { session: { id: 'demo-session', name: '活米村・Orientation 2026', status: 'running', scheduled_start: null, started_at: null, current_period: 2, effective_elapsed_ms: 1260000 }, teams: Array.from({ length: 8 }, (_, index) => ({ id: `demo-team-${index + 1}`, number: index + 1, name: String(index + 1), money: 100 + index * 11 })), markets: [], last_event_sequence: 0 } }
</script>

<style scoped>
.field-board { height: 100%; min-height: 0; }
.boss-board { display: grid; grid-template-columns: minmax(0, .95fr) minmax(0, 1.05fr); grid-template-rows: minmax(0, 1fr) auto; gap: 12px; }
.board-panel { min-width: 0; padding: 16px; background: var(--color-surface); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-md); }
.board-panel__head { display: flex; align-items: start; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.board-panel__head h2 { margin-top: 3px; font-size: 17px; font-weight: 850; }
.board-panel__head p { margin-top: 3px; color: var(--color-muted); font-size: 11px; }
.step-label { color: var(--color-accent); font-size: 11px; font-weight: 850; }
.boss-create { display: flex; flex-direction: column; }
.boss-create .form-grid { gap: 10px; }
.boss-create .form-field { gap: 5px; }
.boss-create .form-field > span { font-size: 11px; }
.boss-create .form-field select { min-height: 42px; }
.question-strip { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 5px 12px; margin-top: 12px; padding: 11px 12px; color: var(--color-ink); background: var(--color-primary-soft); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-sm); }
.question-strip div { display: flex; align-items: baseline; gap: 8px; }
.question-strip strong { font-size: 14px; }
.question-strip span, .question-strip details { color: var(--color-muted); font-size: 11px; }
.question-strip b { color: var(--color-accent); font-size: 15px; white-space: nowrap; }
.question-strip details { grid-column: 1 / -1; }
.question-strip summary { cursor: pointer; font-weight: 800; }
.question-strip p { margin-top: 5px; line-height: 1.5; }
.question-strip small { color: var(--color-accent); }
.board-hint { display: flex; align-items: center; gap: 7px; margin-top: 12px; padding: 10px 12px; color: var(--color-muted); background: var(--color-surface-quiet); border-radius: var(--radius-sm); font-size: 11px; }
.compact-checks { margin-top: 12px !important; }
.check-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.check-row { display: flex; align-items: center; gap: 7px; min-height: 36px; padding: 0 9px; color: var(--color-ink); background: var(--color-surface-quiet); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-sm); font-size: 11px; }
.check-row input { width: 15px; height: 15px; accent-color: var(--color-primary); }
.board-primary-action { width: 100%; min-height: 48px; margin-top: auto; padding-inline: 18px; font-size: 14px; }
.boss-pending { display: flex; flex-direction: column; min-height: 0; }
.fast-list { display: grid; gap: 8px; min-height: 0; overflow: auto; }
.fast-item { padding: 11px; background: var(--color-surface-quiet); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-sm); }
.fast-item__main { display: flex; align-items: center; gap: 9px; }
.fast-item__main > div { display: grid; gap: 2px; min-width: 0; }
.fast-item__main strong { font-size: 13px; }
.fast-item__main span:not(.team-badge) { color: var(--color-muted); font-size: 11px; }
.fast-details { margin: 8px 0; color: var(--color-primary-ink); font-size: 11px; }
.fast-details summary { cursor: pointer; font-weight: 800; }
.fast-details p { margin-top: 4px; color: var(--color-muted); line-height: 1.5; }
.fast-details small { color: var(--color-accent); }
.fast-note { width: 100%; min-height: 32px; margin-top: 9px; padding: 0 9px; color: var(--color-ink); background: var(--color-surface); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-sm); font-size: 11px; }
.fast-actions { display: grid; grid-template-columns: 1fr 84px; gap: 8px; margin-top: 8px; }
.fast-actions .action-button, .fast-actions .ghost-button { min-height: 38px; padding-inline: 9px; font-size: 12px; }
.board-empty { display: grid; place-items: center; align-content: center; gap: 7px; min-height: 180px; color: var(--color-muted); text-align: center; }
.board-empty strong { color: var(--color-ink); font-size: 13px; }
.board-empty span { font-size: 11px; }
.boss-history { grid-column: 1 / -1; padding-block: 11px; }
.boss-history .board-panel__head { align-items: center; margin-bottom: 8px; }
.history-strip { display: flex; gap: 8px; overflow: hidden; }
.history-chip { display: flex; align-items: center; gap: 7px; min-width: 0; padding: 5px 8px 5px 5px; background: var(--color-surface-quiet); border: 1px solid var(--color-border-subtle); border-radius: var(--radius-pill); font-size: 11px; white-space: nowrap; }
.history-chip .team-badge { width: 24px; height: 24px; }
.history-chip > span:not(.team-badge) { overflow: hidden; text-overflow: ellipsis; }
.history-chip b { font-size: 11px; }
.is-success { color: var(--color-success); }
.is-failed { color: var(--color-danger); }
.board-message { grid-column: 1 / -1; display: flex; align-items: center; gap: 7px; margin: -4px 0 0; color: var(--color-success); font-size: 11px; }
.board-message.is-error { color: var(--color-danger); }
@media (max-width: 760px) { .boss-board { height: auto; grid-template-columns: 1fr; grid-template-rows: auto; } .boss-history { grid-column: auto; } .field-board { height: auto; } .board-primary-action { margin-top: 14px; } .history-strip { overflow-x: auto; padding-bottom: 2px; } }
</style>
