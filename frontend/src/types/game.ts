export type Role = 'coordinator' | 'market_master' | 'team_facilitator'
export type SessionStatus = 'draft' | 'scheduled' | 'running' | 'paused' | 'finished'

export interface AccessIdentity {
  access_id: string
  session_id: string
  role: Role
  team_id?: string | null
  market_id?: string | null
  display_name?: string | null
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

export interface MarketSummary {
  id: string
  code: string
  name: string
  owner_team_id?: string | null
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
  resource_type: 'dragon_egg' | 'time_device' | 'unicorn_blood' | 'basilisk_fang'
  buy_price: number
  sell_price: number
  is_public: boolean
}

export interface SetupSnapshot {
  session: { id: string; name: string; status: SessionStatus; scheduled_start?: string | null; current_period: number }
  teams: SetupTeam[]
  markets: SetupMarket[]
  rates: SetupRate[]
}

export interface MarketBoard {
  session: { current_period: number; status: SessionStatus }
  markets: MarketSummary[]
  rates: SetupRate[]
  wallet?: number | null
  inventory: { resource_type: string; quantity: number }[]
}

export interface PendingChallenge {
  id: string
  team_id: string
  team_number: number
  team_name: string
  difficulty_level: number
  created_at: string
}
