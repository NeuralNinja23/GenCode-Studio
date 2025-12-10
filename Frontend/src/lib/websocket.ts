// frontend/src/lib/websocket.ts
/**
 * Centralized WebSocket management for deployment updates
 */

export class DeploymentWebSocket {
  private ws: WebSocket | null = null;
  private projectId: string;
  private listeners: Map<string, Function[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // ms

  constructor(projectId: string) {
    this.projectId = projectId;
  }

  /**
   * Connect to WebSocket server
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/api/deployment/ws?projectId=${this.projectId}`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log(`[WebSocket] Connected for project ${this.projectId}`);
          this.reconnectAttempts = 0;
          this.emit('connected', {});
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.emit(message.type, message);
          } catch (error) {
            console.error('[WebSocket] Failed to parse message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error);
          this.emit('error', { error });
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('[WebSocket] Disconnected');
          this.ws = null;
          this.emit('disconnected', {});
          this.attemptReconnect();
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Attempt to reconnect to WebSocket
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      console.log(`[WebSocket] Attempting reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

      setTimeout(() => {
        this.connect().catch((error) => {
          console.error('[WebSocket] Reconnect failed:', error);
        });
      }, delay);
    } else {
      console.error('[WebSocket] Max reconnection attempts reached');
      this.emit('fatal_error', { message: 'WebSocket connection lost' });
    }
  }

  /**
   * Subscribe to an event type
   */
  on(eventType: string, callback: Function): void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType)!.push(callback);
  }

  /**
   * Unsubscribe from an event type
   */
  off(eventType: string, callback: Function): void {
    const callbacks = this.listeners.get(eventType);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  /**
   * Emit an event to all subscribers
   */
  private emit(eventType: string, data: any): void {
    const callbacks = this.listeners.get(eventType);
    if (callbacks) {
      callbacks.forEach(cb => {
        try {
          cb(data);
        } catch (error) {
          console.error(`[WebSocket] Error in listener for ${eventType}:`, error);
        }
      });
    }
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Close the WebSocket connection
   */
  close(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.listeners.clear();
  }

  /**
   * Send a message through the WebSocket
   */
  send(message: any): void {
    if (this.isConnected()) {
      try {
        this.ws!.send(JSON.stringify(message));
      } catch (error) {
        console.error('[WebSocket] Failed to send message:', error);
      }
    } else {
      console.warn('[WebSocket] Not connected, cannot send message');
    }
  }
}

// Global WebSocket instance management
const websockets = new Map<string, DeploymentWebSocket>();

export function getWebSocket(projectId: string): DeploymentWebSocket {
  if (!websockets.has(projectId)) {
    websockets.set(projectId, new DeploymentWebSocket(projectId));
  }
  return websockets.get(projectId)!;
}

export function closeWebSocket(projectId: string): void {
  const ws = websockets.get(projectId);
  if (ws) {
    ws.close();
    websockets.delete(projectId);
  }
}

export function closeAllWebSockets(): void {
  websockets.forEach((ws) => ws.close());
  websockets.clear();
}

export default {
  DeploymentWebSocket,
  getWebSocket,
  closeWebSocket,
  closeAllWebSockets
};
