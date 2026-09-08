import type { GameConfig, ProductConfig, ResourceKey } from '@/types/game'

type SheetPrices = Record<string, { sell: Record<string, number>; buy: Record<string, number> }>

export const defaultGameConfig: GameConfig = {
  products: [
    { key: 'dragon_egg', name: '龍蛋', short_name: 'A', unit_name: '個' },
    { key: 'time_device', name: '時光器', short_name: 'B', unit_name: '個' },
    { key: 'unicorn_blood', name: '獨角獸的血', short_name: 'C', unit_name: '瓶' },
    { key: 'basilisk_fang', name: '蛇妖牙齒', short_name: 'D', unit_name: '根' },
  ],
  rules: {
    period_count: 4,
    period_duration_minutes: 15,
    trade_quantity: 1,
    same_market_trade_block: true,
    challenge_start_period: 3,
    challenge_default_difficulty: 3,
    challenge_occupied_difficulty: 4,
    challenge_cooldown_minutes: 3,
    ownership_rate_per_minute: 3,
    magic_start_period: 1,
    magic_reward_by_difficulty: [1, 3, 5, 10, 20],
    black_market_start_period: 2,
    black_market_draw_cost: 10,
    guard_money_pouch: true,
    guard_minimum_team_present: true,
  },
  map: {
    image_data_url: null,
    width: null,
    height: null,
  },
}

export function productFor(config: GameConfig | undefined, key: string): ProductConfig {
  return config?.products.find((product) => product.key === key) || defaultGameConfig.products[0]!
}

export function cloneDefaultConfig(): GameConfig {
  return JSON.parse(JSON.stringify(defaultGameConfig)) as GameConfig
}

export function isResourceKey(value: string): value is ResourceKey {
  return defaultGameConfig.products.some((product) => product.key === value)
}

const marketSheet: Record<number, SheetPrices> = {
  1: { A: { sell: { A: 7, C: 4 }, buy: { A: 5 } }, B: { sell: { C: 7, D: 6 }, buy: { B: 6 } }, C: { sell: { B: 4, D: 5 }, buy: { C: 5 } }, D: { sell: { B: 7, C: 5 }, buy: { D: 5 } }, E: { sell: { B: 8, D: 7 }, buy: { A: 6 } }, F: { sell: { A: 6, B: 3 }, buy: { B: 5 } }, G: { sell: { A: 5, C: 5 }, buy: { C: 6 } }, H: { sell: { A: 4, D: 5 }, buy: { D: 6 } } },
  2: { A: { sell: { B: 5, D: 7 }, buy: { A: 3 } }, B: { sell: { A: 4, D: 6 }, buy: { B: 4 } }, C: { sell: { A: 5, B: 5, D: 3 }, buy: { C: 7 } }, D: { sell: { C: 6 }, buy: { D: 7 } }, E: { sell: { B: 7 }, buy: { A: 4 } }, F: { sell: { C: 4, D: 7 }, buy: { B: 6 } }, G: { sell: { C: 7 }, buy: { C: 5 } }, H: { sell: { A: 5, B: 6 }, buy: { D: 4 } } },
  3: { A: { sell: { A: 6, B: 4 }, buy: { A: 4 } }, B: { sell: { C: 7 }, buy: { B: 4 } }, C: { sell: { D: 6 }, buy: { C: 7 } }, D: { sell: { A: 5, B: 5 }, buy: { D: 7 } }, E: { sell: { B: 2, C: 8 }, buy: { A: 8 } }, F: { sell: { C: 4, D: 7 }, buy: { B: 5 } }, G: { sell: { A: 7, C: 3, D: 4 }, buy: { C: 3 } }, H: { sell: { B: 10, D: 5 }, buy: { D: 8 } } },
  4: { A: { sell: { C: 7, D: 2 }, buy: { A: 4 } }, B: { sell: { B: 6, D: 7 }, buy: { B: 4 } }, C: { sell: { A: 5, B: 7 }, buy: { C: 3 } }, D: { sell: { C: 4 }, buy: { D: 3 } }, E: { sell: { A: 7, D: 6 }, buy: { A: 5 } }, F: { sell: { B: 7, D: 7 }, buy: { B: 5 } }, G: { sell: { A: 6, C: 7 }, buy: { C: 6 } }, H: { sell: { B: 8 }, buy: { D: 4 } } },
}

/** Fixed prices from the game sheet, used by the unauthenticated demo too. */
export function defaultMarketRates() {
  return Object.entries(marketSheet).flatMap(([periodText, markets]) => Object.entries(markets).flatMap(([market_code, prices]) => defaultGameConfig.products.map((product) => ({
    market_code,
    period: Number(periodText),
    resource_type: product.key,
    buy_price: prices.buy[product.short_name] || 0,
    sell_price: prices.sell[product.short_name] || 0,
    is_public: true,
  }))))
}
