import { io, Socket } from 'socket.io-client'

export interface WebSocketClient {
  socket: Socket | null
  connect: () => void
  disconnect: () => void
  isConnected: boolean
}

export class FreedomWebSocket implements WebSocketClient {
  public socket: Socket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  constructor(url: string = 'ws://localhost:8080') {
    this.url = url
  }

  connect(): void {
    if (this.socket?.connected) {
      console.log('WebSocket already connected')
      return
    }

    this.socket = io(this.url, {
      transports: ['websocket', 'polling'],
      timeout: 20000,
      reconnection: true,
      reconnectionDelay: this.reconnectDelay,
      reconnectionAttempts: this.maxReconnectAttempts,
    })

    this.socket.on('connect', () => {
      console.log('WebSocket connected successfully')
      this.reconnectAttempts = 0
    })

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason)
    })

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      this.reconnectAttempts++

      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('Max reconnection attempts reached')
        this.disconnect()
      }
    })

    this.socket.on('health_update', (data) => {
      // Emit custom event for health updates
      window.dispatchEvent(new CustomEvent('freedom_health_update', { detail: data }))
    })

    this.socket.on('task_update', (data) => {
      // Emit custom event for task updates
      window.dispatchEvent(new CustomEvent('freedom_task_update', { detail: data }))
    })

    this.socket.on('kb_update', (data) => {
      // Emit custom event for KB updates
      window.dispatchEvent(new CustomEvent('freedom_kb_update', { detail: data }))
    })
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  get isConnected(): boolean {
    return this.socket?.connected ?? false
  }

  // Subscribe to specific events
  subscribe(event: string, callback: (data: unknown) => void): void {
    this.socket?.on(event, callback)
  }

  unsubscribe(event: string, callback?: (data: unknown) => void): void {
    if (callback) {
      this.socket?.off(event, callback)
    } else {
      this.socket?.off(event)
    }
  }

  // Send events
  emit(event: string, data: unknown): void {
    this.socket?.emit(event, data)
  }
}

// Global instance
let wsInstance: FreedomWebSocket | null = null

export const getWebSocketInstance = (): FreedomWebSocket => {
  if (!wsInstance) {
    wsInstance = new FreedomWebSocket()
  }
  return wsInstance
}

// Note: React hooks will be implemented in components using 'use client' directive