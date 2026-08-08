<template>
  <GameShell variant="ceremonial" role-label="隊伍工作區" identity="小隊 7" section="隊伍總覽" kicker="TEAM WORKSPACE" title="" subtitle="" hide-page-heading :nav-items="navItems" :connected="!isDemo" :demo="isDemo" :period="board.session.current_period" :elapsed-ms="board.session.current_period > 0 ? 1260000 : 0" :status="board.session.status" :money="board.wallet ?? 0" @sign-out="goLogin">
    <div class="user-page">
      <section class="user-hero" aria-labelledby="team-hero-title">
        <div class="user-hero__image" aria-hidden="true"></div>
        <div class="user-hero__stars" aria-hidden="true"></div>
        <div class="user-hero__copy">
          <span class="user-kicker">LUMOS · TEAM 07 · FIELD JOURNAL</span>
          <p class="user-hero__period">第 {{ board.session.current_period || '—' }} 段 · {{ phaseLabel }}</p>
          <h1 id="team-hero-title">小隊 7，<em>凱文是給！</em></h1>
          <p class="user-hero__intro">比價每個時段的物價都會波動，記得謹慎</p>
          <div class="user-hero__actions">
            <a class="user-hero__button" href="#market-overview">查看市場行情 <span aria-hidden="true">↓</span></a>
            <span class="user-hero__status"><i aria-hidden="true"></i>{{ isDemo ? '這只是一個純前端展示' : '資料已同步・可以出發' }}</span>
          </div>
        </div>
      </section>

      <section class="user-status" aria-label="小隊目前狀態">
        <div class="user-status__location">
          <span class="user-status__label">目前佔領商會</span>
          <strong>{{ occupiedMarket?.name || '尚未佔領' }}</strong>
          <small>{{ occupiedMarket ? `商會 ${occupiedMarket.code}・收益持續累積中` : '下一站，由你們決定' }}</small>
        </div>
        <div class="user-status__resources" aria-label="現有物資">
          <div v-for="resource in resources" :key="resource.key" class="user-resource">
            <span>{{ resource.name }}</span>
            <strong>{{ resource.amount }}</strong>
          </div>
        </div>
        <div class="user-status__wallet">
          <span>隊伍金錢</span>
          <strong>{{ board.wallet ?? 0 }}</strong>
          <small>枚</small>
        </div>
      </section>

      <section id="market-overview" class="user-workspace" aria-label="小隊工作區">
        <div class="user-market-panel">
          <div class="user-panel-heading">
            <div>
              <span class="user-kicker">THE MARKET CONSTELLATION</span>
              <h2>本段商會行情</h2>
              <p>先比較買入與賣出，再帶著隊伍走向最值得的一站。</p>
            </div>
            <div class="user-panel-heading__meta">
              <span>{{ board.markets.length }} 個商會</span>
              <span>本頁已顯示完整行情</span>
            </div>
          </div>
          <MarketPriceTable :board="board" />
        </div>
      </section>
    </div>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'

import GameShell from '@/layouts/GameShell.vue'
import MarketPriceTable from '@/components/MarketPriceTable.vue'
import { ApiError, getMarketBoard } from '@/lib/api'
import { cloneDefaultConfig } from '@/lib/gameConfig'
import { useSession } from '@/lib/session'
import type { MarketBoard, SetupRate } from '@/types/game'

const router = useRouter()
const { state } = useSession()
const board = reactive<MarketBoard>(demoBoard())
const isDemo = computed(() => !state.token || state.identity?.role !== 'team_facilitator')
const navItems = [{ to: '/user', label: '總覽', icon: 'dashboard' }, { to: '/user/map', label: '市場地圖', icon: 'map' }]
const resources = computed(() => board.config.products.map((product) => ({
  key: product.key,
  name: product.name,
  amount: board.inventory.find((item) => item.resource_type === product.key)?.quantity ?? 0,
})))
const occupiedMarket = computed(() => board.markets.find((market) => market.owner_team_id === state.identity?.team_id || market.owner_team_name === '小隊 7'))
const phaseLabel = computed(() => {
  if (board.session.status === 'running') return '行情正在流動'
  if (board.session.status === 'paused') return '遊戲暫停中'
  if (board.session.status === 'finished') return '本場已結束'
  return '等待遊戲開始'
})
const goLogin = () => router.push('/login')

onMounted(loadBoard)
async function loadBoard() {
  if (isDemo.value || !state.identity || !state.token) return
  try { Object.assign(board, await getMarketBoard(state.identity.session_id, state.token)) } catch (error) { console.warn(error instanceof ApiError ? error.message : '市場行情讀取失敗') }
}

function demoBoard(): MarketBoard {
  const config = cloneDefaultConfig()
  const markets = Array.from({ length: 8 }, (_, index) => { const code = String.fromCharCode(65 + index); return { id: `demo-${index}`, code, name: code, owner_team_id: index === 1 ? 'demo-team-7' : null, owner_team_number: index === 1 ? 7 : null, owner_team_name: index === 1 ? '小隊 7' : null } })
  const rates: SetupRate[] = markets.flatMap((market, marketIndex) => config.products.map((resource, index) => ({ market_code: market.code, period: 2, resource_type: resource.key, buy_price: ([12, 18, 8, 30][index] ?? 0) + marketIndex * 2, sell_price: ([7, 9, 4, 2][index] ?? 0) + marketIndex, is_public: true })))
  return { session: { current_period: 2, status: 'running' }, markets, rates, wallet: 218, inventory: config.products.map((product, index) => ({ resource_type: product.key, quantity: [3, 1, 5, 0][index] ?? 0 })), config }
}
</script>

<style scoped>
.user-page { --user-ink: oklch(.93 .025 90); --user-muted: oklch(.74 .03 255); --user-accent: oklch(.78 .14 80); --user-line: oklch(.78 .14 80 / .28); display: grid; flex: 0 0 auto; gap: 14px; min-height: max-content; color: var(--user-ink); }
.user-hero { position: relative; display: flex; min-height: 224px; overflow: hidden; align-items: stretch; isolation: isolate; background: radial-gradient(circle at 82% 45%, oklch(.29 .13 258 / .27), transparent 24rem), oklch(.1 .04 255); border: 1px solid var(--user-line); }
.user-hero::after { position: absolute; right: 0; bottom: 16px; left: 0; height: 1px; background: var(--user-line); content: ''; }
.user-hero__stars { position: absolute; inset: 0; z-index: -1; opacity: .64; background-image: radial-gradient(circle at 11% 21%, var(--user-accent) 0 1px, transparent 1.8px), radial-gradient(circle at 25% 74%, var(--user-ink) 0 1px, transparent 1.8px), radial-gradient(circle at 56% 14%, var(--user-accent) 0 1px, transparent 1.8px), radial-gradient(circle at 89% 25%, var(--user-ink) 0 1px, transparent 1.8px), radial-gradient(circle at 93% 75%, var(--user-accent) 0 1px, transparent 1.8px); animation: user-stars-breathe 12s ease-in-out infinite alternate; }
.user-hero__image { position: absolute; inset: 0; z-index: -2; background-image: linear-gradient(90deg, oklch(.1 .04 255 / .99) 0%, oklch(.1 .04 255 / .9) 44%, oklch(.1 .04 255 / .7) 100%), url('/orientation-hero.jpg'); background-position: center, 80% 44%; background-size: cover, cover; opacity: .1; filter: saturate(.8) contrast(1.06); }
.user-hero__copy { position: relative; z-index: 2; display: flex; max-width: 780px; flex: 1 1 auto; flex-direction: column; justify-content: center; padding: 26px clamp(24px, 4vw, 64px) 30px; }
.user-kicker { display: block; color: var(--user-accent); font-size: 10px; letter-spacing: .17em; }
.user-hero__period { margin-top: 19px; color: var(--user-muted); font-size: 12px; letter-spacing: .04em; }
.user-hero h1 { margin-top: 10px; color: var(--user-ink); font-family: 'Noto Serif TC', 'Source Han Serif TC', Georgia, serif; font-size: clamp(30px, 3vw, 44px); font-weight: 500; line-height: 1.08; letter-spacing: -.025em; text-shadow: 0 2px 0 oklch(.05 .02 250 / .28); }
.user-hero h1 em { color: var(--user-accent); font-style: normal; }
.user-hero__intro { max-width: 58ch; margin-top: 14px; color: var(--user-muted); font-size: 12px; line-height: 1.7; }
.user-hero__actions { display: flex; align-items: center; flex-wrap: wrap; gap: 16px; margin-top: 18px; }
.user-hero__button { position: relative; display: inline-flex; align-items: center; justify-content: center; gap: 17px; min-height: 40px; padding: 0 15px; color: var(--user-accent); border: 1px solid var(--user-accent); font-family: 'Noto Serif TC', 'Source Han Serif TC', Georgia, serif; font-size: 12px; transition: color 180ms ease-out, background 180ms ease-out, transform 180ms ease-out; }
.user-hero__button::before { position: absolute; inset: 4px; border: 1px solid oklch(.78 .14 80 / .2); content: ''; pointer-events: none; }
.user-hero__button:hover { color: oklch(.1 .04 255); background: var(--user-accent); transform: translateY(-2px); }
.user-hero__button span { font-size: 18px; }
.user-hero__status { display: inline-flex; align-items: center; gap: 8px; color: var(--user-muted); font-size: 11px; }
.user-hero__status i { width: 7px; height: 7px; background: var(--color-success); border: 1px solid var(--color-success); border-radius: 50%; box-shadow: 0 0 0 4px oklch(.72 .12 151 / .12); }
.user-status { display: grid; grid-template-columns: minmax(190px, .85fr) minmax(0, 1.65fr) 150px; gap: 13px; align-items: stretch; margin-top: 0; padding: 15px 17px; color: var(--user-ink); background: oklch(.2 .06 255); border: 1px solid var(--user-line); border-radius: 10px; }
.user-status__location { display: grid; align-content: center; gap: 3px; min-width: 0; }.user-status__label, .user-status__wallet span { color: var(--user-muted); font-size: 10px; }.user-status__location strong { overflow: hidden; font-family: 'Noto Serif TC', 'Source Han Serif TC', Georgia, serif; font-size: 18px; text-overflow: ellipsis; white-space: nowrap; }.user-status__location small { overflow: hidden; color: var(--user-muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.user-status__resources { display: grid; grid-template-columns: repeat(auto-fit, minmax(84px, 1fr)); gap: 8px; min-width: 0; }.user-resource { display: grid; align-content: center; gap: 5px; min-width: 0; padding: 8px 10px; background: oklch(.12 .045 255 / .56); }.user-resource span { overflow: hidden; color: var(--user-muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }.user-resource strong { color: var(--user-accent); font-size: 20px; font-variant-numeric: tabular-nums; }
.user-status__wallet { display: grid; align-content: center; gap: 2px; padding-left: 16px; border-left: 1px solid var(--user-line); }.user-status__wallet strong { color: var(--user-accent); font-family: Georgia, serif; font-size: 28px; font-variant-numeric: tabular-nums; }.user-status__wallet small { color: var(--user-muted); font-size: 10px; }
.user-workspace { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-items: start; }.user-market-panel { position: relative; min-width: 0; padding: 19px; background: oklch(.19 .045 255); border: 1px solid var(--user-line); border-radius: 10px; }.user-market-panel::before { position: absolute; top: 8px; left: 8px; width: 12px; height: 12px; border-top: 1px solid var(--user-accent); border-left: 1px solid var(--user-accent); content: ''; opacity: .72; }.user-panel-heading { display: flex; align-items: start; justify-content: space-between; gap: 16px; margin-bottom: 15px; }.user-panel-heading h2 { margin-top: 6px; color: var(--user-ink); font-family: 'Noto Serif TC', 'Source Han Serif TC', Georgia, serif; font-size: 20px; font-weight: 700; }.user-panel-heading p { margin-top: 4px; color: var(--user-muted); font-size: 11px; line-height: 1.55; }.user-panel-heading__meta { display: grid; justify-items: end; gap: 8px; color: var(--user-muted); font-size: 10px; white-space: nowrap; }.user-panel-heading__meta a { color: var(--user-accent); transition: color 160ms ease-out; }.user-panel-heading__meta a:hover { color: var(--user-ink); }.user-panel-heading__meta a span { margin-left: 4px; font-size: 14px; }
.user-market-panel :deep(.market-table-wrap) { border-color: oklch(.78 .14 80 / .18); }.user-market-panel :deep(.market-price-table thead th) { color: var(--user-ink); background: oklch(.27 .08 255); border-color: oklch(.78 .14 80 / .18); }.user-market-panel :deep(.market-price-table thead th small), .user-market-panel :deep(.market-table-note) { color: var(--user-muted); }.user-market-panel :deep(.market-price-table tbody th), .user-market-panel :deep(.market-price-table tbody td) { background: oklch(.16 .04 255); border-color: oklch(.78 .14 80 / .14); }.user-market-panel :deep(.market-price-table tbody tr:hover th), .user-market-panel :deep(.market-price-table tbody tr:hover td) { background: oklch(.22 .055 255); }.user-market-panel :deep(.market-price-table .market-row__name strong), .user-market-panel :deep(.market-price-table .price-line strong) { color: var(--user-ink); }.user-market-panel :deep(.market-price-table .price-line:first-child strong) { color: var(--color-primary-ink); }.user-market-panel :deep(.market-price-table .price-line:last-child strong) { color: var(--color-success); }
@keyframes user-stars-breathe { from { opacity: .48; } to { opacity: .88; } }
@media (max-width: 980px) { .user-status { grid-template-columns: minmax(160px, .8fr) minmax(0, 1.5fr) 120px; } }
@media (max-width: 700px) { .user-page { gap: 12px; }.user-hero { min-height: 248px; }.user-hero__copy { max-width: none; padding: 26px 20px 30px; }.user-status { grid-template-columns: 1fr 1fr; gap: 12px; padding: 14px; }.user-status__location { grid-column: 1 / -1; padding-bottom: 10px; border-bottom: 1px solid var(--user-line); }.user-status__wallet { padding-left: 12px; }.user-panel-heading { flex-direction: column; }.user-panel-heading__meta { width: 100%; align-items: start; justify-items: start; }.user-market-panel { padding: 16px; } }
@media (prefers-reduced-motion: reduce) { .user-hero__stars { animation: none; } }
</style>
