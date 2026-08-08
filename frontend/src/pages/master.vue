<template>
  <GameShell role-label="市場關主台" identity="B-02・西廂市場" section="市場工作台" kicker="MARKET MASTER DESK" title="西廂市場，準備開市。" subtitle="這裡只顯示你的市場、當期行情與待判定事件，讓每次互動都能快速完成。" :nav-items="navItems" :connected="!isDemo" :demo="isDemo" :period="2" :elapsed-ms="1260000" status="running" :money="0" @sign-out="goLogin">
    <template #heading-actions><button class="ghost-button" type="button"><Icon name="map" size="sm" />查看地圖位置</button><button class="action-button" type="button"><Icon name="spark" size="sm" />呼叫總召</button></template>
    <div class="notice"><Icon name="alert" size="sm" /><span><strong>互動提醒：</strong>每次交易、挑戰與判題都要確認金錢袋已出示，並且至少半數隊員在場。</span></div>
    <section class="section-block"><div class="section-block__head"><div><h2>第 2 時段行情</h2><p>部分極端行情只對關主與總召可見</p></div><span class="status-badge is-success">市場營運中</span></div><table class="data-table"><thead><tr><th>原料</th><th>買入</th><th>賣出</th><th>公開狀態</th><th>操作</th></tr></thead><tbody><tr v-for="rate in rates" :key="rate.name"><td><div class="team-cell"><span class="team-badge">{{ rate.mark }}</span><div><strong>{{ rate.name }}</strong><span>{{ rate.note }}</span></div></div></td><td class="money-value">{{ rate.buy }} 枚</td><td>{{ rate.sell }} 枚</td><td><span class="status-badge" :class="rate.hidden ? 'is-warning' : 'is-neutral'">{{ rate.hidden ? '隱藏行情' : '網站公開' }}</span></td><td><button class="text-button" type="button">交易紀錄 →</button></td></tr></tbody></table></section>
    <div v-if="message" class="form-message" :class="{ 'is-error': messageType === 'error' }"><Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}</div><div class="two-column"><section class="section-block"><div class="section-block__head"><div><h2>目前佔領</h2><p>成功挑戰後會即時替換</p></div><span class="status-badge is-success">月桂會</span></div><div class="empty-state"><Icon name="map" size="lg" /><strong>月桂會正在守住西廂市場</strong><p>目前收益 3 枚／分鐘。若有隊伍發起挑戰，請在此處理結果。</p><button class="ghost-button" type="button" style="margin-top: 14px">查看佔領紀錄</button></div></section><section class="section-block"><div class="section-block__head"><div><h2>待判定挑戰</h2><p>實體活動由你輸入結果</p></div><span class="status-badge is-warning">{{ challenges.length }} 筆待處理</span></div><div v-if="challenges.length" class="event-list"><div v-for="challenge in challenges" :key="challenge.id" class="event-item"><span class="event-icon"><Icon name="team" size="sm" /></span><div><strong>{{ challenge.team_name || challenge.team }} 發起挑戰</strong><span>市場守衛・難度 {{ challenge.difficulty_level || challenge.level }}</span></div><div class="decision-actions"><button class="text-button" type="button" @click="grade(challenge.id, true)">成功</button><button class="text-button is-danger" type="button" @click="grade(challenge.id, false)">失敗</button></div></div></div><div v-else class="empty-state"><Icon name="check" size="lg" /><strong>目前沒有待判定挑戰</strong><p>新的挑戰送出後會即時出現在這裡。</p></div></section></div>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, getPendingChallenges, gradeChallenge } from '@/lib/api'
import { useSession } from '@/lib/session'
import type { PendingChallenge } from '@/types/game'

const router = useRouter()
const { state } = useSession()
const isDemo = computed(() => !state.token || state.identity?.role !== 'market_master')
const navItems = [{ to: '/master', label: '市場工作台', icon: 'market' }, { to: '/master/rates', label: '當期行情', icon: 'dashboard' }, { to: '/master/challenges', label: '待判定挑戰', icon: 'spark' }]
const rates = [{ mark: '龍', name: '龍蛋', note: '高風險原料', buy: 12, sell: 7, hidden: false }, { mark: '時', name: '時光器', note: '稀有物資', buy: 18, sell: 9, hidden: true }, { mark: '血', name: '獨角獸的血', note: '藥劑原料', buy: 8, sell: 4, hidden: false }, { mark: '牙', name: '蛇妖牙齒', note: '極端行情', buy: 30, sell: 2, hidden: true }]
const challenges = ref<(PendingChallenge & { team?: string; level?: number })[]>([{ id: 'demo-challenge-1', team_id: 'demo-team-4', team_number: 4, team_name: '星火隊', team: '星火隊', difficulty_level: 3, level: 3, created_at: new Date().toISOString() }, { id: 'demo-challenge-2', team_id: 'demo-team-11', team_number: 11, team_name: '銀月旅團', team: '銀月旅團', difficulty_level: 4, level: 4, created_at: new Date().toISOString() }])
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
onMounted(loadChallenges)
async function loadChallenges() {
  if (isDemo.value || !state.identity?.market_id || !state.token) return
  try { challenges.value = await getPendingChallenges(state.identity.market_id, state.token) } catch (error) { showError(error) }
}
async function grade(challengeId: string, success: boolean) {
  if (isDemo.value) { challenges.value = challenges.value.filter((challenge) => challenge.id !== challengeId); messageType.value = 'success'; message.value = success ? '展示判定成功，原隊伍會開始佔領計時。' : '展示判定失敗，系統會套用 3 分鐘冷卻。'; return }
  if (!state.token) return
  try { await gradeChallenge(challengeId, success, undefined, state.token); challenges.value = challenges.value.filter((challenge) => challenge.id !== challengeId); messageType.value = 'success'; message.value = success ? '挑戰成功，佔領狀態已更新。' : '挑戰失敗，冷卻時間已建立。' } catch (error) { showError(error) }
}
function showError(error: unknown) { messageType.value = 'error'; message.value = error instanceof ApiError ? error.message : '目前無法更新挑戰結果。' }
const goLogin = () => router.push('/login')
</script>

<style scoped>
.decision-actions { display: flex; align-items: center; gap: 10px; }
.decision-actions .is-danger { color: var(--color-danger); }
</style>
