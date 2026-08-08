import type { GameConfig, ProductConfig, ResourceKey } from '@/types/game'

export const defaultGameConfig: GameConfig = {
  products: [
    { key: 'dragon_egg', name: 'A', short_name: 'A', unit_name: '個' },
    { key: 'time_device', name: 'B', short_name: 'B', unit_name: '個' },
    { key: 'unicorn_blood', name: 'C', short_name: 'C', unit_name: '瓶' },
    { key: 'basilisk_fang', name: 'D', short_name: 'D', unit_name: '根' },
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
