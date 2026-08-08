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

