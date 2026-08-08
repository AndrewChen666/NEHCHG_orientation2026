import { computed, reactive } from 'vue'

import { getMe, getSnapshot, login } from '@/lib/api'
import type { AccessIdentity, GameSnapshot } from '@/types/game'

const tokenKey = 'active-magic-village-token'
const identityKey = 'active-magic-village-identity'

const state = reactive<{ token: string | null; identity: AccessIdentity | null; snapshot: GameSnapshot | null }>({
  token: localStorage.getItem(tokenKey),
  identity: JSON.parse(localStorage.getItem(identityKey) || 'null') as AccessIdentity | null,
  snapshot: null,
})

export function useSession() {
  const isAuthenticated = computed(() => Boolean(state.token && state.identity))

  async function signIn(sessionId: string, accessCode: string) {
    const result = await login(sessionId, accessCode)
    state.token = result.token
    state.identity = result.access
    localStorage.setItem(tokenKey, result.token)
    localStorage.setItem(identityKey, JSON.stringify(result.access))
    return result.access
  }

  async function restore() {
    if (!state.token) return null
    try {
      state.identity = await getMe(state.token)
      state.snapshot = await getSnapshot(state.identity.session_id, state.token)
      return state.identity
    } catch {
      signOut()
      return null
    }
  }

  function signOut() {
    state.token = null
    state.identity = null
    state.snapshot = null
    localStorage.removeItem(tokenKey)
    localStorage.removeItem(identityKey)
  }

  return { state, isAuthenticated, signIn, restore, signOut }
}

