export type Role = 'coordinator' | 'magic_boss' | 'market_master' | 'team_facilitator'
export type SessionStatus = 'draft' | 'scheduled' | 'running' | 'paused' | 'finished'
/** Per-session product identifiers are editable, so this is intentionally not a fixed union. */
export type ResourceKey = string

export interface ProductConfig {
  key: ResourceKey
  name: string
  short_name: string
  unit_name: string
}

export interface GameRules {
  period_count: number
  period_duration_minutes: number
  trade_quantity: number
  same_market_trade_block: boolean
  challenge_start_period: number
  challenge_default_difficulty: number
  challenge_occupied_difficulty: number
  challenge_cooldown_minutes: number
  ownership_rate_per_minute: number
  magic_start_period: number
  magic_reward_by_difficulty: number[]
  black_market_start_period: number
  black_market_draw_cost: number
  guard_money_pouch: boolean
  guard_minimum_team_present: boolean
}

export interface MapConfig {
  image_data_url: string | null
  width: number | null
  height: number | null
}

export interface GameConfig {
  products: ProductConfig[]
  rules: GameRules
  map: MapConfig
}

export interface AccessIdentity {
  access_id: string
  session_id: string
  role: Role
  team_id?: string | null
  market_id?: string | null
  display_name?: string | null
}

export interface AccessCodeSummary {
  access_id: string
  role: Role
  display_name: string
  team_id?: string | null
  market_id?: string | null
  active: boolean
}

export interface SessionSummary {
  id: string
  name: string
  status: SessionStatus
  scheduled_start?: string | null
  started_at?: string | null
  current_period: number
  effective_elapsed_ms: number
}

export interface TeamSummary {
  id: string
  number: number
  name: string
  money: number
}

export interface TeamPublicProfile {
  number: number
  name: string
  english_name: string
  icon: string
  description: string
  tone: string
}

export interface PublicHomeContent {
  session: { id: string; name: string; status: SessionStatus; scheduled_start?: string | null } | null
  teams: TeamPublicProfile[]
}

export interface MarketSummary {
  id: string
  code: string
  name: string
  owner_team_id?: string | null
  owner_team_number?: number | null
  owner_team_name?: string | null
  owner_started_elapsed_ms?: number | null
}

export interface GameSnapshot {
  session: SessionSummary
  teams: TeamSummary[]
  markets: MarketSummary[]
  last_event_sequence: number
}

export interface GameEvent {
  sequence?: number
  type: string
  session_id?: string
  occurred_at?: string
  payload?: Record<string, unknown>
}

export interface SetupTeam {
  id: string
  number: number
  name: string
  english_name: string
  icon: string
  description: string
  tone: string
  initial_money: number
  initial_inventory: Record<string, number>
}

export interface SetupMarket {
  id: string
  code: string
  name: string
  map_x?: number | null
  map_y?: number | null
}

export interface SetupRate {
  market_code: string
  period: number
  resource_type: ResourceKey
  buy_price: number
  sell_price: number
  is_public: boolean
}

export interface SetupSnapshot {
  session: { id: string; name: string; status: SessionStatus; scheduled_start?: string | null; current_period: number }
  config: GameConfig
  teams: SetupTeam[]
  markets: SetupMarket[]
  rates: SetupRate[]
}

export interface MarketBoard {
  session: { current_period: number; status: SessionStatus; effective_elapsed_ms?: number }
  config: GameConfig
  markets: MarketSummary[]
  rates: SetupRate[]
  teams?: MarketTeamSummary[]
  wallet?: number | null
  inventory: { resource_type: string; quantity: number }[]
}

export interface MarketTeamSummary {
  id: string
  number: number
  name: string
  money: number
  inventory: Record<string, number>
}

export interface PendingChallenge {
  id: string
  team_id: string
  team_number: number
  team_name: string
  difficulty_level: number
  result?: 'success' | 'failed' | null
  ownership_applied_at?: string | null
  created_at: string
}

export interface MagicQuestion {
  id: string
  subject: string
  difficulty_level: number
  reward: number
  prompt?: string | null
  answer_note?: string | null
}

export interface PendingMagicChallenge {
  id: string
  team_id: string
  team_number: number
  team_name: string
  subject: string
  difficulty_level: number
  prompt: string
  answer_note?: string | null
  reward: number
  created_at: string
}

export interface MagicChallengeHistory extends PendingMagicChallenge {
  result: 'success' | 'failed'
  note?: string | null
  judged_at?: string | null
}

export interface BlackMarketEffect {
  id: string
  name: string
  description: string
  effect_type: string
  effect_config?: Record<string, unknown>
  requires_manual_apply: boolean
  replayed?: boolean
}
