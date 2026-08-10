import type { AccessIdentity, ActivitySnapshot, ActivityStage, BlackMarketEffect, GameConfig, GameSnapshot, Leaderboards, MagicChallengeHistory, MagicQuestion, MarketBoard, ParticipantRecord, PendingChallenge, PendingMagicChallenge, PublicHomeContent, Role, RoleAssignmentRecord, ScoreTargets, SessionSummary, SetupMarket, SetupRate, SetupSnapshot, SetupTeam } from '@/types/game'

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

export async function googleLogin(credential: string, role?: Role) {
  return request<{ access: AccessIdentity; token: string }>('/api/v1/auth/google', {
    method: 'POST',
    body: JSON.stringify({ credential, role }),
  })
}

export async function getMe(token: string) {
  return request<AccessIdentity>('/api/v1/auth/me', {}, token)
}

export async function getPublicHome() {
  return request<PublicHomeContent>('/api/v1/public/home')
}

export async function getSnapshot(sessionId: string, token: string) {
  return request<GameSnapshot>(`/api/v1/sessions/${sessionId}/snapshot`, {}, token)
}

export async function getGameConfig(sessionId: string, token: string) {
  return request<GameConfig>(`/api/v1/sessions/${sessionId}/config`, {}, token)
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

export async function updateConfig(sessionId: string, config: GameConfig, token: string) {
  return request<{ updated: boolean }>(`/api/v1/setup/sessions/${sessionId}/config`, {
    method: 'PUT',
    body: JSON.stringify(config),
  }, token)
}

export async function getActivity(sessionId: string, token: string) {
  return request<ActivitySnapshot>(`/api/v1/sessions/${sessionId}/activity`, {}, token)
}

export async function getParticipants(sessionId: string, token: string) {
  return request<ParticipantRecord[]>(`/api/v1/sessions/${sessionId}/participants`, {}, token)
}

export async function importParticipants(sessionId: string, csvText: string, token: string) {
  return request<{ created: number; updated: number; total: number }>(`/api/v1/setup/sessions/${sessionId}/participants/import`, {
    method: 'POST',
    body: JSON.stringify({ csv_text: csvText }),
  }, token)
}

export async function getActivityStages(sessionId: string, token: string) {
  return request<ActivityStage[]>(`/api/v1/setup/sessions/${sessionId}/stages`, {}, token)
}

export async function updateActivityStages(sessionId: string, stages: ActivityStage[], token: string) {
  return request<{ updated: number }>(`/api/v1/setup/sessions/${sessionId}/stages`, {
    method: 'PUT',
    body: JSON.stringify({ stages }),
  }, token)
}

export async function setActiveStage(sessionId: string, stageId: string | null, token: string) {
  return request<{ stage_id: string | null }>(`/api/v1/sessions/${sessionId}/active-stage`, {
    method: 'PUT',
    body: JSON.stringify({ stage_id: stageId }),
  }, token)
}

export async function getRoleAssignments(sessionId: string, token: string) {
  return request<RoleAssignmentRecord[]>(`/api/v1/setup/sessions/${sessionId}/role-assignments`, {}, token)
}

export async function updateRoleAssignments(sessionId: string, assignments: RoleAssignmentRecord[], token: string) {
  return request<{ updated: number }>(`/api/v1/setup/sessions/${sessionId}/role-assignments`, {
    method: 'PUT',
    body: JSON.stringify({ assignments }),
  }, token)
}

export async function getScoreTargets(sessionId: string, token: string) {
  return request<ScoreTargets>(`/api/v1/sessions/${sessionId}/score-targets`, {}, token)
}

export async function saveIcebreakerGroup(payload: { stage_id: string; round_number: number; group_number: number; participant_ids: string[]; round_name?: string }, token: string) {
  return request<{ round_number: number; group_number: number; members: ParticipantRecord[]; warnings: Array<{ participant_id: string; shared_count: number }> }>(`/api/v1/stages/${payload.stage_id}/icebreaker/groups`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }, token)
}

export async function getIcebreakerRecommendations(stageId: string, roundNumber: number, groupNumber: number | null, token: string) {
  const params = new URLSearchParams({ round_number: String(roundNumber) })
  if (groupNumber !== null) params.set('group_number', String(groupNumber))
  return request<Array<{ id: string; participant_no: string; display_name: string; shared_count: number; never_shared: boolean }>>(`/api/v1/stages/${stageId}/icebreaker/recommendations?${params}`, {}, token)
}

export async function recordScore(payload: { stage_id: string; target_type: 'personal' | 'team' | 'college'; target_id: string; points: number; note?: string; idempotency_key: string }, token: string) {
  return request<{ id: string; points: number; target_type: string; target_id: string; replayed: boolean }>(`/api/v1/stages/${payload.stage_id}/scores`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }, token)
}

export async function getLeaderboards(sessionId: string, stageId: string | null, token: string) {
  const query = stageId ? `?stage_id=${encodeURIComponent(stageId)}` : ''
  return request<Leaderboards>(`/api/v1/sessions/${sessionId}/leaderboards${query}`, {}, token)
}

export async function getMarketBoard(sessionId: string, token: string) {
  return request<MarketBoard>(`/api/v1/sessions/${sessionId}/markets`, {}, token)
}

export async function updateMarketOwnership(marketId: string, teamId: string | null, token: string) {
  return request<{ market_id: string; team_id: string | null; ownership_applied: boolean }>(`/api/v1/markets/${marketId}/ownership`, {
    method: 'PUT',
    body: JSON.stringify({ team_id: teamId }),
  }, token)
}

export async function recordMarketFailure(payload: { market_id: string; team_id: string; note?: string; idempotency_key: string }, token: string) {
  return request<{ id: string; result: string; replayed: boolean }>(`/api/v1/markets/${payload.market_id}/challenge-failures`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }, token)
}

export async function createTransaction(payload: {
  market_id: string
  team_id: string
  resource_type: SetupRate['resource_type']
  direction: 'buy' | 'sell'
  quantity: number
  money_pouch_presented: boolean
  minimum_team_present: boolean
  idempotency_key: string
}, token: string) {
  return request<{ id: string; amount: number; quantity: number; replayed: boolean }>('/api/v1/markets/' + payload.market_id + '/transactions', {
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

export async function applyChallengeOwnership(challengeId: string, token: string) {
  return request<{ id: string; result: string; ownership_applied: boolean; team_id: string }>(`/api/v1/challenges/${challengeId}/ownership`, {
    method: 'POST',
  }, token)
}

export async function getMagicQuestions(sessionId: string, token: string) {
  return request<MagicQuestion[]>(`/api/v1/sessions/${sessionId}/magic/questions`, {}, token)
}

export async function createMagicChallenge(payload: { team_id: string; question_id: string; money_pouch_presented: boolean; minimum_team_present: boolean; idempotency_key: string }, token: string) {
  return request<{ id: string; status: string; replayed: boolean }>('/api/v1/magic-challenges', { method: 'POST', body: JSON.stringify(payload) }, token)
}

export async function getPendingMagicChallenges(sessionId: string, token: string) {
  return request<PendingMagicChallenge[]>(`/api/v1/sessions/${sessionId}/magic-challenges/pending`, {}, token)
}

export async function getMagicChallengeHistory(sessionId: string, token: string) {
  return request<MagicChallengeHistory[]>(`/api/v1/sessions/${sessionId}/magic-challenges/history`, {}, token)
}

export async function gradeMagicChallenge(challengeId: string, success: boolean, note: string | undefined, token: string) {
  return request<{ id: string; result: string; reward: number }>(`/api/v1/magic-challenges/${challengeId}/result`, {
    method: 'POST',
    body: JSON.stringify({ success, note }),
  }, token)
}

export async function drawBlackMarketCard(payload: { money_pouch_presented: boolean; minimum_team_present: boolean; idempotency_key: string }, token: string) {
  return request<BlackMarketEffect>('/api/v1/black-market/draw', { method: 'POST', body: JSON.stringify(payload) }, token)
}

export async function applyBlackMarketEffect(effectId: string, note: string | undefined, token: string) {
  return request<{ id: string; status: string; requires_manual_apply: boolean }>(`/api/v1/black-market/effects/${effectId}/apply`, { method: 'POST', body: JSON.stringify({ note }) }, token)
}

export function roleLabel(role: Role) {
  const labels: Record<Role, string> = {
    coordinator: '總召控制台',
    participant: '參加者工作區',
    icebreaker_facilitator: '破冰隊輔台',
    score_keeper: '活動記分台',
    magic_boss: '隱藏魔王工作台',
    market_master: '市場關主台',
    team_facilitator: '隊伍工作區',
  }
  return labels[role]
}

export { apiBase }
