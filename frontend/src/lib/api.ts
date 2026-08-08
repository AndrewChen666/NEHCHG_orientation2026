import type { AccessIdentity, GameSnapshot, MarketBoard, PendingChallenge, Role, SessionSummary, SetupMarket, SetupRate, SetupSnapshot, SetupTeam } from '@/types/game'

const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

interface ApiErrorPayload {
  error?: { code?: string; message?: string; details?: Record<string, unknown> }
  detail?: { code?: string; message?: string; details?: Record<string, unknown> } | string
}

export class ApiError extends Error {
  code: string
  details?: Record<string, unknown>
  status: number

  constructor(message: string, status: number, code = 'REQUEST_FAILED', details?: Record<string, unknown>) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers || {}),
    },
  })

  const body = (await response.json().catch(() => ({}))) as ApiErrorPayload | T
  if (!response.ok) {
    const detail = body as ApiErrorPayload
    const error = detail.error || detail.detail
    if (typeof error === 'string') throw new ApiError(error, response.status)
    throw new ApiError(error?.message || '伺服器暫時無法完成操作。', response.status, error?.code, error?.details)
  }
  return body as T
}

export async function login(sessionId: string, accessCode: string) {
  return request<{ access: AccessIdentity; token: string }>('/api/v1/auth/code-login', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, access_code: accessCode }),
  })
}

export async function getMe(token: string) {
  return request<AccessIdentity>('/api/v1/auth/me', {}, token)
}

export async function getSnapshot(sessionId: string, token: string) {
  return request<GameSnapshot>(`/api/v1/sessions/${sessionId}/snapshot`, {}, token)
}

export async function updateClock(sessionId: string, action: 'start' | 'pause' | 'resume' | 'finish', token: string) {
  return request<{ session: SessionSummary; event_sequence?: number }>(`/api/v1/sessions/${sessionId}/${action}`, {
    method: 'POST',
  }, token)
}

export async function getSetup(sessionId: string, token: string) {
  return request<SetupSnapshot>(`/api/v1/setup/sessions/${sessionId}`, {}, token)
}

export async function updateTeams(sessionId: string, teams: SetupTeam[], token: string) {
  return request<{ updated: number }>(`/api/v1/setup/sessions/${sessionId}/teams`, {
    method: 'PUT',
    body: JSON.stringify(teams),
  }, token)
}

export async function updateMarkets(sessionId: string, markets: SetupMarket[], token: string) {
  return request<{ updated: number }>(`/api/v1/setup/sessions/${sessionId}/markets`, {
    method: 'PUT',
    body: JSON.stringify(markets),
  }, token)
}

export async function updateRates(sessionId: string, rates: SetupRate[], token: string) {
  return request<{ updated: number }>(`/api/v1/setup/sessions/${sessionId}/rates`, {
    method: 'PUT',
    body: JSON.stringify({ rates }),
  }, token)
}

export async function getMarketBoard(sessionId: string, token: string) {
  return request<MarketBoard>(`/api/v1/sessions/${sessionId}/markets`, {}, token)
}

export async function createTransaction(payload: {
  market_id: string
  resource_type: SetupRate['resource_type']
  direction: 'buy' | 'sell'
  money_pouch_presented: boolean
  minimum_team_present: boolean
  idempotency_key: string
}, token: string) {
  return request<{ id: string; amount: number; replayed: boolean }>('/api/v1/markets/' + payload.market_id + '/transactions', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, token)
}

export async function createMarketChallenge(payload: {
  market_id: string
  difficulty_level: number
  money_pouch_presented: boolean
  minimum_team_present: boolean
  idempotency_key: string
}, token: string) {
  return request<{ id: string; status: string; replayed: boolean }>('/api/v1/markets/' + payload.market_id + '/challenge', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, token)
}

export async function getPendingChallenges(marketId: string, token: string) {
  return request<PendingChallenge[]>(`/api/v1/markets/${marketId}/challenges/pending`, {}, token)
}

export async function gradeChallenge(challengeId: string, success: boolean, note: string | undefined, token: string) {
  return request<{ id: string; result: string; cooldown_until_effective_ms?: number | null }>(`/api/v1/challenges/${challengeId}/result`, {
    method: 'POST',
    body: JSON.stringify({ success, note }),
  }, token)
}

export function roleLabel(role: Role) {
  return {
    coordinator: '總召控制台',
    market_master: '市場關主台',
    team_facilitator: '隊伍工作區',
  }[role]
}

export { apiBase }
