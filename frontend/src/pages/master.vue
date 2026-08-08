<template>
  <GameShell role-label="市場關主台" identity="B-02・西廂市場" section="市場工作台" kicker="MARKET MASTER DESK" title="西廂市場，準備開市。" subtitle="這裡只顯示你的市場、當期行情與待判定事件，讓每次互動都能快速完成。" :nav-items="navItems" :connected="false" demo :period="2" :elapsed-ms="1260000" status="running" :money="0" @sign-out="goLogin">
    <template #heading-actions><button class="ghost-button" type="button"><Icon name="map" size="sm" />查看地圖位置</button><button class="action-button" type="button"><Icon name="spark" size="sm" />呼叫總召</button></template>
    <div class="notice"><Icon name="alert" size="sm" /><span><strong>互動提醒：</strong>每次交易、挑戰與判題都要確認金錢袋已出示，並且至少半數隊員在場。</span></div>
    <section class="section-block"><div class="section-block__head"><div><h2>第 2 時段行情</h2><p>部分極端行情只對關主與總召可見</p></div><span class="status-badge is-success">市場營運中</span></div><table class="data-table"><thead><tr><th>原料</th><th>買入</th><th>賣出</th><th>公開狀態</th><th>操作</th></tr></thead><tbody><tr v-for="rate in rates" :key="rate.name"><td><div class="team-cell"><span class="team-badge">{{ rate.mark }}</span><div><strong>{{ rate.name }}</strong><span>{{ rate.note }}</span></div></div></td><td class="money-value">{{ rate.buy }} 枚</td><td>{{ rate.sell }} 枚</td><td><span class="status-badge" :class="rate.hidden ? 'is-warning' : 'is-neutral'">{{ rate.hidden ? '隱藏行情' : '網站公開' }}</span></td><td><button class="text-button" type="button">交易紀錄 →</button></td></tr></tbody></table></section>
    <div class="two-column"><section class="section-block"><div class="section-block__head"><div><h2>目前佔領</h2><p>成功挑戰後會即時替換</p></div><span class="status-badge is-success">月桂會</span></div><div class="empty-state"><Icon name="map" size="lg" /><strong>月桂會正在守住西廂市場</strong><p>目前收益 3 枚／分鐘。若有隊伍發起挑戰，請在此處理結果。</p><button class="ghost-button" type="button" style="margin-top: 14px">查看佔領紀錄</button></div></section><section class="section-block"><div class="section-block__head"><div><h2>待判定挑戰</h2><p>實體活動由你輸入結果</p></div><span class="status-badge is-warning">2 筆待處理</span></div><div class="event-list"><div v-for="challenge in challenges" :key="challenge.team" class="event-item"><span class="event-icon"><Icon name="team" size="sm" /></span><div><strong>{{ challenge.team }} 發起挑戰</strong><span>{{ challenge.note }}</span></div><button class="text-button" type="button">判定</button></div></div></section></div>
  </GameShell>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'

const router = useRouter()
const navItems = [{ to: '/master', label: '市場工作台', icon: 'market' }, { to: '/master/rates', label: '當期行情', icon: 'dashboard' }, { to: '/master/challenges', label: '待判定挑戰', icon: 'spark' }]
const rates = [{ mark: '龍', name: '龍蛋', note: '高風險原料', buy: 12, sell: 7, hidden: false }, { mark: '時', name: '時光器', note: '稀有物資', buy: 18, sell: 9, hidden: true }, { mark: '血', name: '獨角獸的血', note: '藥劑原料', buy: 8, sell: 4, hidden: false }, { mark: '牙', name: '蛇妖牙齒', note: '極端行情', buy: 30, sell: 2, hidden: true }]
const challenges = [{ team: '星火隊', note: '坐式排球・難度 III' }, { team: '銀月旅團', note: '市場守衛・難度 IV' }]
const goLogin = () => router.push('/login')
</script>
