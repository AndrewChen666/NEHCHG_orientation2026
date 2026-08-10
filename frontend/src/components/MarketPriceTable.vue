<template>
  <div v-if="board.markets.length && resources.length" class="market-table-wrap">
    <table class="market-price-table">
      <caption class="sr-only">第 {{ board.session.current_period || '—' }} 段所有商會的商品買入與賣出價格</caption>
      <colgroup><col class="market-price-table__col--market" /><col v-for="resource in resources" :key="resource.key" class="market-price-table__col--product" /></colgroup>
      <thead><tr><th scope="col">商會</th><th v-for="resource in resources" :key="resource.key" scope="col"><span>{{ resource.short_name }}</span><small>{{ resource.name }}・{{ resource.unit_name }}</small></th></tr></thead>
      <tbody>
        <tr v-for="market in board.markets" :key="market.id">
          <th scope="row" class="market-price-table__market-cell"><div class="market-row"><span class="market-code">{{ market.code }}</span><span class="market-row__name"><strong>{{ market.name }}</strong><small>{{ market.owner_team_name ? `佔領：${market.owner_team_name}` : '尚未佔領' }}</small></span></div></th>
          <td v-for="resource in resources" :key="resource.key"><div class="price-cell" :class="{ 'is-unavailable': !rateFor(market.code, resource.key) }"><div class="price-line"><span>買入</span><strong>{{ displayPrice(rateFor(market.code, resource.key)?.buy_price) }}</strong></div><div class="price-line"><span>賣出</span><strong>{{ displayPrice(rateFor(market.code, resource.key)?.sell_price) }}</strong></div></div></td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-else class="board-empty board-empty--short"><Icon name="alert" size="sm" /><strong>目前沒有可顯示的行情</strong></div>
  <p class="market-table-note"><Icon name="info" size="sm" />買入／賣出以每次交易 {{ board.config.rules.trade_quantity }} 單位顯示；「—」代表尚未設定或目前未公開。</p>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import Icon from '@/components/Icon.vue'
import type { MarketBoard } from '@/types/game'

const props = defineProps<{ board: MarketBoard }>()
const resources = computed(() => props.board.config.products)

function rateFor(marketCode: string, resourceType: string) {
  return props.board.rates.find((rate) => rate.market_code === marketCode && rate.period === props.board.session.current_period && rate.resource_type === resourceType)
}

function displayPrice(value?: number | null) {
  return value && value > 0 ? value * props.board.config.rules.trade_quantity : '—'
}
</script>

<style scoped>
.market-table-wrap { max-width: 100%; overflow: auto; border: 1px solid var(--color-border); border-radius: var(--radius-sm); overscroll-behavior: contain; }
.market-price-table { width: 100%; min-width: 920px; table-layout: fixed; border-collapse: separate; border-spacing: 0; }
.market-price-table__col--market { width: 168px; }
.market-price-table__col--product { width: 188px; }
.market-price-table th, .market-price-table td { border-bottom: 1px solid var(--color-border); border-right: 1px solid var(--color-border); }
.market-price-table tr:last-child th, .market-price-table tr:last-child td { border-bottom: 0; }
.market-price-table th:last-child, .market-price-table td:last-child { border-right: 0; }
.market-price-table thead th { position: sticky; top: 0; z-index: 2; padding: 9px 10px; color: var(--color-primary-ink); background: var(--color-primary-soft); text-align: left; }
.market-price-table thead th:first-child { left: 0; z-index: 4; }
.market-price-table thead th span, .market-price-table thead th small { display: block; }
.market-price-table thead th span { font-size: 13px; font-weight: 850; }
.market-price-table thead th small { margin-top: 3px; color: var(--color-muted); font-size: 10px; font-weight: 500; }
.market-price-table tbody th, .market-price-table tbody td { padding: 10px; background: var(--color-surface-raised); }
.market-price-table__market-cell { position: sticky; left: 0; z-index: 1; text-align: left; }
.market-row { display: flex; align-items: center; gap: 8px; min-width: 0; }
.market-code { display: grid; width: 28px; height: 28px; flex: 0 0 auto; place-items: center; color: var(--color-ink); background: var(--color-primary); border-radius: 50%; font-size: 12px; font-weight: 850; }
.market-row__name { display: grid; min-width: 0; gap: 3px; }
.market-row__name strong, .market-row__name small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.market-row__name strong { color: var(--color-ink); font-size: 12px; }
.market-row__name small { color: var(--color-muted); font-size: 10px; font-weight: 500; }
.price-cell { display: grid; gap: 6px; }
.price-line { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; color: var(--color-muted); font-size: 10px; }
.price-line strong { color: var(--color-ink); font-size: 15px; font-variant-numeric: tabular-nums; }
.price-line:first-child strong { color: var(--color-primary-ink); }
.price-line:last-child strong { color: var(--color-success); }
.price-cell.is-unavailable .price-line strong { color: var(--color-muted); font-weight: 600; }
.market-table-note { display: flex; align-items: center; gap: 6px; min-width: 0; margin-top: 9px; color: var(--color-muted); font-size: 10px; overflow-wrap: anywhere; }
.market-table-note .icon { flex: 0 0 auto; color: var(--color-primary); }
.board-empty--short { min-height: 70px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
@media (max-width: 1023px) { .market-price-table { width: 920px; min-width: 920px; } }
@media (max-width: 560px) { .market-table-wrap { width: calc(100% + 28px); margin-inline: -14px; border-width: 1px 0; border-radius: 0; } .market-price-table { width: 920px; min-width: 920px; } .market-table-note { align-items: flex-start; line-height: 1.5; } }
</style>
