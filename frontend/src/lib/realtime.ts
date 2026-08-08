import type { GameEvent } from '@/types/game'

export type RealtimeStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'

export class GameRealtime {
  private socket: WebSocket | null = null
  private readonly listeners = new Set<(event: GameEvent) => void>()
  private reconnectTimer: number | undefined
  private shouldReconnect = true
  status: RealtimeStatus = 'idle'

  connect(sessionId: string, token: string) {
    this.shouldReconnect = true
    this.status = 'connecting'
    const url = new URL(`/api/v1/sessions/${sessionId}/stream`, import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000')
    url.searchParams.set('token', token)
    this.socket = new WebSocket(url)
    this.socket.onopen = () => {
      this.status = 'connected'
      this.socket?.send('ping')
    }
    this.socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as GameEvent
      this.listeners.forEach((listener) => listener(event))
    }
    this.socket.onclose = () => {
      this.status = 'disconnected'
      if (this.shouldReconnect) this.scheduleReconnect(sessionId, token)
    }
    this.socket.onerror = () => {
      this.status = 'error'
    }
  }

  onEvent(listener: (event: GameEvent) => void) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  disconnect() {
    this.shouldReconnect = false
    if (this.reconnectTimer) window.clearTimeout(this.reconnectTimer)
    this.socket?.close()
    this.socket = null
    this.status = 'idle'
  }

  private scheduleReconnect(sessionId: string, token: string) {
    if (this.reconnectTimer) window.clearTimeout(this.reconnectTimer)
    this.reconnectTimer = window.setTimeout(() => this.connect(sessionId, token), 2500)
  }
}
