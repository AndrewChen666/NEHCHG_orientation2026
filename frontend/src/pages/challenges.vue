<template>
  <GameShell role-label="隊伍工作區" identity="第 7 隊・鳳凰社" section="挑戰與魔王" kicker="ENCOUNTERS" title="把運氣交給命運。" subtitle="魔王題目由指定角色現場判定；黑心商人卡片只會從總召啟用的牌堆中抽出。" :nav-items="navItems" :connected="!isDemo" :demo="isDemo" :period="2" :elapsed-ms="1260000" status="running" :money="wallet" @sign-out="goLogin">
    <template #heading-actions><span class="status-badge is-warning">每次互動需 2 項現場確認</span></template>
    <div class="notice"><Icon name="alert" size="sm" /><span><strong>請記得：</strong>出示金錢袋、確認至少半數隊員在場。這兩項條件會跟著請求送到後端，不能只在畫面上勾選。</span></div>
    <div class="two-column">
      <section class="section-block"><div class="section-block__head"><div><h2>隱藏魔王</h2><p>六個學科、五種難度；成功後由判定角色發放獎勵</p></div><span class="status-badge is-success">I–V</span></div><div class="form-grid two-up"><label class="form-field"><span>學科</span><select v-model="subject"><option v-for="item in subjects" :key="item" :value="item">{{ item }}</option></select></label><label class="form-field"><span>難度</span><select v-model.number="difficulty"><option v-for="level in 5" :key="level" :value="level">難度 {{ roman(level) }}・{{ rewards[level - 1] }} 金幣</option></select></label></div><div class="question-preview"><span class="eyebrow">SELECTED QUEST</span><strong>{{ selectedQuestion ? `已找到 ${subject}・難度 ${roman(difficulty)} 題目` : '目前尚未建立這個難度的題目' }}</strong><p>{{ selectedQuestion ? '題目內容會由現場魔王角色向隊伍口頭提出，隊伍端不顯示答案。' : '請由總召在題庫中建立題目後再挑戰。' }}</p></div><button class="action-button" type="button" :disabled="!selectedQuestion || submitting" @click="openMagic">{{ submitting ? '送出中…' : '發起隱藏魔王挑戰' }}<Icon name="spark" size="sm" /></button></section>

      <section class="section-block"><div class="section-block__head"><div><h2>黑心商人</h2><p>第 2 時段起可用，抽卡前會扣除 10 枚金幣</p></div><span class="status-badge is-warning">10 枚／次</span></div><div v-if="drawnCard" class="drawn-card"><span class="eyebrow">CARD DRAWN</span><strong>{{ drawnCard.name }}</strong><p>{{ drawnCard.description }}</p><span class="status-badge is-warning">待人工套用</span><button class="ghost-button" type="button" :disabled="submitting" @click="applyCard">{{ submitting ? '處理中…' : '確認已套用效果' }}</button></div><div v-else class="empty-state"><Icon name="spark" size="lg" /><strong>牌堆尚未翻開</strong><p>抽卡會扣除 10 枚金幣；缺少已啟用卡片時，系統會拒絕扣款。</p><button class="action-button" type="button" :disabled="wallet < 10 || submitting" @click="openBlackCard">抽取一張卡</button></div></section>
    </div>

    <section v-if="action" class="section-block interaction-section"><div class="section-block__head"><div><h2>確認現場條件</h2><p>{{ action === 'magic' ? '向隱藏魔王發起挑戰' : '向黑心商人購買一次抽卡機會' }}</p></div><Icon name="wallet" size="md" /></div><div class="check-grid"><label class="check-row"><input v-model="guards.money" type="checkbox" /><span>我已確認金錢袋同時出示</span></label><label class="check-row"><input v-model="guards.team" type="checkbox" /><span>我已確認至少半數隊員在場</span></label></div><p v-if="message" class="form-message" :class="{ 'is-error': messageType === 'error' }"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</p><div class="form-actions"><button class="ghost-button" type="button" @click="closeAction">取消</button><button class="action-button" type="button" :disabled="!guards.money || !guards.team || submitting" @click="submitAction">{{ submitting ? '送出中…' : action === 'magic' ? '送出魔王挑戰' : '確認抽卡' }}</button></div></section>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, applyBlackMarketEffect, createMagicChallenge, drawBlackMarketCard, getMagicQuestions } from '@/lib/api'
import { useSession } from '@/lib/session'
import type { BlackMarketEffect, MagicQuestion } from '@/types/game'

const router = useRouter()
const { state } = useSession()
const navItems = [{ to: '/user', label: '隊伍總覽', icon: 'dashboard' }, { to: '/user/market', label: '市場交易', icon: 'market' }, { to: '/user/challenges', label: '挑戰與魔王', icon: 'spark' }, { to: '/user/map', label: '市場地圖', icon: 'map' }]
const subjects = ['數學', '自然', '資訊', '語文', '社會', '生活']
const rewards = [1, 3, 5, 10, 20]
const questions = ref<MagicQuestion[]>(demoQuestions())
const subject = ref('數學')
const difficulty = ref(2)
const wallet = ref(218)
const action = ref<'magic' | 'black' | null>(null)
const guards = reactive({ money: false, team: false })
const drawnCard = ref<BlackMarketEffect | null>(null)
const submitting = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const isDemo = computed(() => !state.token || state.identity?.role !== 'team_facilitator')
const selectedQuestion = computed(() => questions.value.find((question) => question.subject === subject.value && question.difficulty_level === difficulty.value))

onMounted(loadQuestions)
async function loadQuestions() { if (!isDemo.value && state.identity && state.token) { try { questions.value = await getMagicQuestions(state.identity.session_id, state.token) } catch (error) { showError(error) } } }
function openMagic() { action.value = 'magic'; clearMessage() }
function openBlackCard() { action.value = 'black'; clearMessage() }
function closeAction() { action.value = null; guards.money = false; guards.team = false }
async function submitAction() {
  if (!action.value) return
  submitting.value = true
  try {
    if (isDemo.value) { messageType.value = 'success'; message.value = action.value === 'magic' ? '展示挑戰已送出，請等待指定角色判定。' : '展示抽卡已完成，正式場次會扣除 10 枚金幣。'; if (action.value === 'black') wallet.value -= 10; closeAction(); return }
    if (!state.token || !selectedQuestion.value || !state.identity) return
    if (action.value === 'magic') await createMagicChallenge({ question_id: selectedQuestion.value.id, money_pouch_presented: guards.money, minimum_team_present: guards.team, idempotency_key: requestId() }, state.token)
    else { drawnCard.value = await drawBlackMarketCard({ money_pouch_presented: guards.money, minimum_team_present: guards.team, idempotency_key: requestId() }, state.token); wallet.value -= 10 }
    messageType.value = 'success'; message.value = action.value === 'magic' ? '魔王挑戰已送到判定角色。' : '抽卡成功，請依卡片說明由現場角色套用。'; closeAction()
  } catch (error) { showError(error) } finally { submitting.value = false }
}
async function applyCard() { if (!drawnCard.value || isDemo.value || !state.token) { drawnCard.value = null; return } submitting.value = true; try { await applyBlackMarketEffect(drawnCard.value.id, undefined, state.token); messageType.value = 'success'; message.value = '效果已記錄為套用。' ; drawnCard.value = null } catch (error) { showError(error) } finally { submitting.value = false } }
function roman(level: number) { return ['I', 'II', 'III', 'IV', 'V'][level - 1] }
function requestId() { return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `special-${Date.now()}` }
function clearMessage() { message.value = '' }
function showError(error: unknown) { messageType.value = 'error'; message.value = error instanceof ApiError ? error.message : '目前無法完成這個互動。' }
function goLogin() { router.push('/login') }
function demoQuestions(): MagicQuestion[] { return subjects.flatMap((item) => Array.from({ length: 5 }, (_, index) => ({ id: `demo-${item}-${index + 1}`, subject: item, difficulty_level: index + 1, reward: rewards[index] }))) }
</script>

<style scoped>
.question-preview { display: grid; gap: 7px; margin: 20px 0; padding: 16px; background: var(--color-primary-soft); border-radius: var(--radius-sm); }
.question-preview strong { color: var(--color-primary-strong); font-size: 15px; }
.question-preview p { color: var(--color-muted); font-size: 12px; line-height: 1.6; }
.drawn-card { display: grid; gap: 12px; min-height: 220px; padding: 20px; color: white; background: var(--color-primary); border-radius: var(--radius-md); }
.drawn-card strong { color: var(--color-accent); font-family: 'Noto Serif TC', serif; font-size: 24px; }
.drawn-card p { color: oklch(0.88 0.02 252); font-size: 13px; line-height: 1.7; }
.drawn-card .status-badge { width: fit-content; color: var(--color-primary-strong); background: var(--color-accent); }
.drawn-card .ghost-button { width: fit-content; color: white; background: transparent; border-color: oklch(0.75 0.04 252 / .6); }
.interaction-section { border-color: var(--color-primary); }
.check-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.check-row { display: flex; align-items: center; gap: 9px; min-height: 44px; padding: 0 12px; color: var(--color-ink); background: var(--color-surface); border-radius: var(--radius-sm); font-size: 12px; }
.check-row input { width: 16px; height: 16px; accent-color: var(--color-primary); }
@media (max-width: 760px) { .check-grid { grid-template-columns: 1fr; } }
</style>
