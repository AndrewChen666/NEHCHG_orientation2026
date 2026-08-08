<template>
  <GameShell role-label="隊伍工作區" identity="第 7 隊・鳳凰社" section="我的隊伍" kicker="TEAM WORKSPACE" title="鳳凰社，下一步怎麼走？" subtitle="在市場之間移動、觀察行情，讓每一枚金幣都替你靠近終點。" :nav-items="navItems" :connected="false" demo :period="2" :elapsed-ms="1260000" status="running" :money="218" @sign-out="goLogin">
    <template #heading-actions><button class="ghost-button" type="button"><Icon name="map" size="sm" />市場地圖</button><button class="action-button" type="button"><Icon name="wallet" size="sm" />查看資產明細</button></template>
    <div class="notice"><Icon name="spark" size="sm" /><span><strong>隊伍提示：</strong>西廂市場出現隱藏行情，但你們剛剛已在那裡交易；下一筆請先移動到其他市場。</span></div>
    <section class="section-block"><div class="section-block__head"><div><h2>我的資產</h2><p>最後同步：剛剛・代表隊輔：林同學</p></div><span class="status-badge is-success">隊伍在線</span></div><div class="resource-list"><div class="resource-item"><span>金幣</span><strong>218</strong></div><div v-for="resource in resources" :key="resource.name" class="resource-item"><span>{{ resource.name }}</span><strong>{{ resource.amount }}</strong></div></div></section>
    <div class="two-column"><section class="section-block"><div class="section-block__head"><div><h2>現在可以做什麼</h2><p>互動前會再次確認現場條件</p></div></div><div class="action-grid"><button v-for="action in actions" :key="action.label" class="action-tile" type="button"><span class="action-tile__icon"><Icon :name="action.icon" size="md" /></span><strong>{{ action.label }}</strong><span>{{ action.detail }}</span></button></div></section><section class="section-block"><div class="section-block__head"><div><h2>隊伍紀錄</h2><p>最近的金錢與物資變化</p></div><button class="text-button" type="button">全部紀錄 →</button></div><div class="event-list"><div v-for="event in events" :key="event.title" class="event-item"><span class="event-icon"><Icon :name="event.icon" size="sm" /></span><div><strong>{{ event.title }}</strong><span>{{ event.detail }}</span></div><span class="event-time">{{ event.time }}</span></div></div></section></div>
  </GameShell>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'

const router = useRouter()
const navItems = [{ to: '/user', label: '隊伍總覽', icon: 'dashboard' }, { to: '/user/market', label: '市場交易', icon: 'market' }, { to: '/user/challenges', label: '挑戰與魔王', icon: 'spark' }, { to: '/user/map', label: '市場地圖', icon: 'map' }]
const resources = [{ name: '龍蛋', amount: 3 }, { name: '時光器', amount: 1 }, { name: '獨角獸的血', amount: 5 }]
const actions = [{ icon: 'market', label: '前往市場交易', detail: '查看八個市場的當期行情' }, { icon: 'spark', label: '挑戰隱藏魔王', detail: '答題成功可獲得金幣' }, { icon: 'map', label: '挑戰據點', detail: '第 3 時段起開放佔領' }]
const events = [{ icon: 'market', title: '買入龍蛋 × 1', detail: '北塔市場・支出 12 枚', time: '2 分鐘前' }, { icon: 'spark', title: '魔王題目挑戰成功', detail: '自然科・難度 II・獲得 3 枚', time: '6 分鐘前' }, { icon: 'wallet', title: '取得開局金幣', detail: '總召設定・+200 枚', time: '剛開始' }]
const goLogin = () => router.push('/login')
</script>
