<template>
  <GameShell
    role-label="總召控制台"
    identity="活米村・主控席"
    section="總覽"
    kicker="COORDINATOR DESK"
    title="今天，先看全局。"
    subtitle="掌握四個時段的節奏、八個市場的佔領狀態，以及每一枚金幣的去向。"
    :nav-items="navItems"
    :connected="false"
    demo
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
      <div class="stat-item is-accent"><span>目前時段</span><strong>第 2 段</strong><em>還有 02:54</em></div>
      <div class="stat-item"><span>場上總金幣</span><strong>1,248</strong><em>較開局 +18.4%</em></div>
      <div class="stat-item"><span>已佔領據點</span><strong>5 / 8</strong><em>3 個市場仍開放</em></div>
      <div class="stat-item"><span>待處理事件</span><strong>03</strong><em>需要關主判定</em></div>
    </div>

    <div class="two-column">
      <section class="section-block">
        <div class="section-block__head"><div><h2>隊伍金幣排行</h2><p>即時同步・依目前金錢袋排序</p></div><button class="text-button" type="button">查看完整榜單 →</button></div>
        <table class="data-table"><thead><tr><th>隊伍</th><th>金幣</th><th>資產趨勢</th><th>狀態</th></tr></thead><tbody>
          <tr v-for="team in teams" :key="team.number"><td><div class="team-cell"><span class="team-badge">{{ team.number }}</span><div><strong>{{ team.name }}</strong><span>{{ team.note }}</span></div></div></td><td class="money-value">{{ team.money.toLocaleString() }}</td><td><div class="rank-bar"><span :style="{ width: `${team.ratio}%` }" /></div></td><td><span class="status-badge" :class="team.statusClass">{{ team.status }}</span></td></tr>
        </tbody></table>
      </section>
      <section class="section-block"><div class="section-block__head"><div><h2>最新事件</h2><p>所有操作均保留紀錄</p></div><span class="status-badge is-success">即時</span></div><div class="event-list">
        <div v-for="event in events" :key="event.title" class="event-item"><span class="event-icon"><Icon :name="event.icon" size="sm" /></span><div><strong>{{ event.title }}</strong><span>{{ event.detail }}</span></div><span class="event-time">{{ event.time }}</span></div>
      </div></section>
    </div>

    <div class="three-column">
      <section class="section-block"><div class="section-block__head"><div><h2>市場佔領</h2><p>時段 2 尚未開放挑戰</p></div><Icon name="map" size="md" /></div><div class="market-list"><div v-for="market in markets" :key="market.code" class="market-row"><div class="market-row__name"><span class="market-code">{{ market.code }}</span><div><strong>{{ market.name }}</strong><span>{{ market.owner }}</span></div></div><span class="status-badge" :class="market.owner === '開放中' ? 'is-neutral' : 'is-success'">{{ market.owner === '開放中' ? '待佔領' : '已佔領' }}</span></div></div></section>
      <section class="section-block"><div class="section-block__head"><div><h2>遊戲時鐘</h2><p>可排程，也可手動控制</p></div><Icon name="clock" size="md" /></div><div class="notice"><Icon name="spark" size="sm" /><span>目前以伺服器時間計算。若現場需要調整，所有覆寫都會進入稽核紀錄。</span></div><div class="inline-row" style="margin-top: 18px"><span class="mini-label">下一段將於 13:30 自動開始</span><button class="ghost-button" type="button">暫停</button></div></section>
      <section class="section-block"><div class="section-block__head"><div><h2>快速設定</h2><p>開局資料與事件資料</p></div><Icon name="dashboard" size="md" /></div><div class="action-grid" style="grid-template-columns: 1fr 1fr"><button v-for="item in quickActions" :key="item.label" class="action-tile" type="button"><span class="action-tile__icon"><Icon :name="item.icon" size="sm" /></span><strong>{{ item.label }}</strong><span>{{ item.detail }}</span></button></div></section>
    </div>
  </GameShell>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

import GameShell from '@/layouts/GameShell.vue'
import Icon from '@/components/Icon.vue'

const router = useRouter()
const navItems = [{ to: '/admin', label: '總覽', icon: 'dashboard' }, { to: '/admin/markets', label: '市場與行情', icon: 'market' }, { to: '/admin/teams', label: '隊伍資產', icon: 'team' }, { to: '/admin/map', label: '地圖與佔領', icon: 'map' }]
const teams = [
  { number: 7, name: '鳳凰社', note: '剛完成一筆交易', money: 218, ratio: 100, status: '領先中', statusClass: 'is-success' },
  { number: 3, name: '月桂會', note: '持有 2 個據點', money: 196, ratio: 90, status: '持有據點', statusClass: 'is-warning' },
  { number: 11, name: '銀月旅團', note: '魔王挑戰成功', money: 171, ratio: 79, status: '活躍', statusClass: 'is-success' },
  { number: 2, name: '星火隊', note: '等待下一場行情', money: 155, ratio: 71, status: '觀望中', statusClass: 'is-neutral' },
]
const events = [{ icon: 'market', title: '鳳凰社完成交易', detail: '在北塔市場買入龍蛋 × 1', time: '剛剛' }, { icon: 'spark', title: '月桂會佔領成功', detail: '西廂市場開始計算收益', time: '1 分鐘前' }, { icon: 'alert', title: '有 3 個挑戰待判定', detail: '請提醒對應關主處理', time: '3 分鐘前' }]
const markets = [{ code: 'A', name: '北塔市場', owner: '鳳凰社' }, { code: 'B', name: '西廂市場', owner: '月桂會' }, { code: 'C', name: '鐘樓市場', owner: '開放中' }]
const quickActions = [{ icon: 'market', label: '編輯行情', detail: '管理公開與隱藏價格' }, { icon: 'spark', label: '題目與卡片', detail: '設定可抽取內容' }]
const goLogin = () => router.push('/login')
</script>
