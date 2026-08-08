<template>
  <GameShell
    role-label="總召控制台"
    identity="活米村・主控席"
    :nav-items="navItems"
    :hide-page-heading="true"
    :connected="!isDemo"
    :demo="isDemo"
    :period="2"
    :elapsed-ms="1260000"
    status="running"
    :money="0"
    @sign-out="goLogin"
  >
    <template #heading-actions>
      <button class="ghost-button" type="button"><Icon name="clock" size="sm" />時段控制</button>
      <button class="action-button" type="button"><Icon name="spark" size="sm" />發佈公告</button>
    </template>

    <div class="stat-grid">
      <div class="stat-item is-accent">
        <div class="stat-item__topline"><span>目前時段</span><span class="live-mark"><i />進行中</span></div>
        <div class="stat-item__value-row"><strong>第 2 段</strong><em>02:54</em></div>
        <span class="stat-item__meta">距離下一段</span>
      </div>
      <div class="stat-item"><span>場上總金幣</span><strong>1,248</strong><em class="is-positive">↗ 較開局 +18.4%</em></div>
      <div class="stat-item"><span>已佔領據點</span><strong>5<span class="stat-item__unit"> / 8</span></strong><em>3 個市場仍開放</em></div>
      <div class="stat-item"><span>待處理事件</span><strong>03</strong><em class="is-alert">需要現場角色處理</em></div>
    </div>

    <div class="two-column">
      <section class="section-block leaderboard-panel">
        <div class="section-block__head"><div><h2>隊伍金幣排行</h2><p>即時同步・依目前金錢袋排序</p></div><button class="text-button" type="button">查看完整榜單 →</button></div>
        <table class="data-table"><thead><tr><th>隊伍</th><th>金幣</th><th>資產趨勢</th><th>狀態</th></tr></thead><tbody>
          <tr v-for="team in teams" :key="team.number"><td><div class="team-cell"><span class="team-badge">{{ team.number }}</span><div><strong>{{ team.name }}</strong><span>{{ team.note }}</span></div></div></td><td class="money-value">{{ team.money.toLocaleString() }}</td><td><div class="rank-bar"><span :style="{ width: `${team.ratio}%` }" /></div></td><td><span class="status-badge" :class="team.statusClass">{{ team.status }}</span></td></tr>
        </tbody></table>
      </section>
      <section class="section-block events-panel"><div class="section-block__head"><div><h2>最新事件</h2><p>所有操作均保留紀錄</p></div><span class="status-badge is-success">即時</span></div><div class="event-list">
        <div v-for="event in events" :key="event.title" class="event-item" :class="`is-${event.tone}`"><span class="event-icon"><Icon :name="event.icon" size="sm" /></span><div><strong>{{ event.title }}</strong><span>{{ event.detail }}</span></div><span class="event-time">{{ event.time }}</span></div>
      </div></section>
    </div>

    <section class="section-block magic-owner-note">
      <div class="section-block__head"><div><h2>隱藏魔王事件</h2><p>魔王挑戰與結果由專用的「隱藏魔王工作台」操作，總召不在這裡判題。</p></div><span class="status-badge is-neutral">權限分離</span></div>
      <div class="notice"><Icon name="spark" size="sm" /><span>請將魔王代碼交給現場魔王；題庫、現場挑戰、成功發獎與失敗紀錄都會在魔王工作台完成。</span></div>
    </section>

    <div class="three-column">
      <section class="section-block"><div class="section-block__head"><div><h2>市場佔領</h2><p>時段 2 尚未開放挑戰</p></div><Icon name="map" size="md" /></div><div class="market-list"><div v-for="market in markets" :key="market.code" class="market-row"><div class="market-row__name"><span class="market-code">{{ market.code }}</span><div><strong>{{ market.name }}</strong><span>{{ market.owner }}</span></div></div><span class="status-badge" :class="market.owner === '開放中' ? 'is-neutral' : 'is-success'">{{ market.owner === '開放中' ? '待佔領' : '已佔領' }}</span></div></div></section>
      <section class="section-block"><div class="section-block__head"><div><h2>遊戲時鐘</h2><p>可排程，也可手動控制</p></div><Icon name="clock" size="md" /></div><div class="notice"><Icon name="spark" size="sm" /><span>目前以伺服器時間計算。若現場需要調整，所有覆寫都會進入稽核紀錄。</span></div><div class="inline-row" style="margin-top: 18px"><span class="mini-label">下一段將於 13:30 自動開始</span><button class="ghost-button" type="button">暫停</button></div></section>
      <section class="section-block"><div class="section-block__head"><div><h2>快速設定</h2><p>開局資料與事件資料</p></div><Icon name="dashboard" size="md" /></div><div class="action-grid" style="grid-template-columns: 1fr 1fr"><RouterLink v-for="item in quickActions" :key="item.label" :to="item.to" class="action-tile"><span class="action-tile__icon"><Icon :name="item.icon" size="sm" /></span><strong>{{ item.label }}</strong><span>{{ item.detail }}</span></RouterLink></div></section>
    </div>
  </GameShell>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useSession } from '@/lib/session'
import GameShell from '@/layouts/GameShell.vue'
import Icon from '@/components/Icon.vue'

const router = useRouter()
const { state } = useSession()
const isDemo = computed(() => !state.token || state.identity?.role !== 'coordinator')
const navItems = [{ to: '/admin', label: '總覽', icon: 'dashboard' }, { to: '/admin/setup', label: '開局設定', icon: 'spark' }, { to: '/admin/markets', label: '市場與行情', icon: 'market' }, { to: '/admin/teams', label: '隊伍資產', icon: 'team' }, { to: '/admin/map', label: '地圖與佔領', icon: 'map' }]
const teams = [
  { number: 7, name: '7', note: '剛完成一筆交易', money: 218, ratio: 100, status: '領先中', statusClass: 'is-success' },
  { number: 3, name: '3', note: '持有 2 個據點', money: 196, ratio: 90, status: '持有據點', statusClass: 'is-warning' },
  { number: 8, name: '8', note: '魔王挑戰成功', money: 171, ratio: 79, status: '活躍', statusClass: 'is-success' },
  { number: 2, name: '2', note: '等待下一場行情', money: 155, ratio: 71, status: '觀望中', statusClass: 'is-neutral' },
]
const events = [{ icon: 'market', title: '小隊 7 完成交易', detail: '在 A 市場買入資源 A × 1', time: '剛剛', tone: 'trade' }, { icon: 'spark', title: '小隊 3 佔領成功', detail: 'B 市場開始計算收益', time: '1 分鐘前', tone: 'capture' }, { icon: 'alert', title: '有 3 個現場事件待處理', detail: '請提醒對應角色處理', time: '3 分鐘前', tone: 'alert' }]
const markets = [{ code: 'A', name: 'A', owner: '小隊 7' }, { code: 'B', name: 'B', owner: '小隊 3' }, { code: 'C', name: 'C', owner: '開放中' }]
const quickActions = [{ icon: 'spark', label: '開局設定', detail: '隊伍、資產與市場位置', to: '/admin/setup' }, { icon: 'market', label: '編輯行情', detail: '管理公開與隱藏價格', to: '/admin/markets' }]
const goLogin = () => router.push('/login')

</script>

<style scoped>
.magic-owner-note { margin-top: 24px; }
</style>
