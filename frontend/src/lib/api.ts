import type { AccessIdentity, GameSnapshot, Role, SessionSummary } from '@/types/game'

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

export function roleLabel(role: Role) {
  return {
    coordinator: '總召控制台',
    market_master: '市場關主台',
    team_facilitator: '隊伍工作區',
  }[role]
}

export { apiBase }

