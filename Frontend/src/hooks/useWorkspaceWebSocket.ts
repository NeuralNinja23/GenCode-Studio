import { useEffect, useRef, useState, useCallback } from 'react';
import { getApiUrl } from '../config/env';

export interface ChatMessage {
    id: string;
    sender: 'user' | 'agent';
    content: string;
    timestamp?: number;
}

interface UseWorkspaceWebSocketOptions {
    projectId: string | undefined;
    initialPrompt: string | null;
    onMessage?: (message: any) => void;
    onWorkflowUpdate?: (stage: number, stepName: string) => void;
    onPause?: (message: string) => void;
    onComplete?: () => void;
    onError?: (error: string) => void;
}

export const useWorkspaceWebSocket = ({
    projectId,
    initialPrompt,
    onMessage,
    onWorkflowUpdate,
    onPause,
    onComplete,
    onError,
}: UseWorkspaceWebSocketOptions) => {
    const ws = useRef<WebSocket | null>(null);
    const hasStartedGeneration = useRef(false);
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState<string | null>(null);

    const connect = useCallback(() => {
        if (!projectId) return;

        try {
            const apiUrl = getApiUrl('');
            const wsUrl = apiUrl.replace(/^http/, 'ws');
            const wsEndpoint = `${wsUrl}/ws/workspace/${projectId}`;

            ws.current = new WebSocket(wsEndpoint);

            ws.current.onopen = () => {
                console.log('[WS] Connected');
                setIsConnected(true);
                setConnectionError(null);

                // Send initial prompt if provided
                if (initialPrompt && !hasStartedGeneration.current) {
                    hasStartedGeneration.current = true;
                    ws.current?.send(
                        JSON.stringify({
                            type: 'user_message',
                            content: initialPrompt,
                        })
                    );
                }
            };

            ws.current.onclose = (event) => {
                console.log('[WS] Disconnected', event.code, event.reason);
                setIsConnected(false);

                // Auto-reconnect on abnormal closure
                if (event.code !== 1000 && event.code !== 1001) {
                    setTimeout(() => {
                        console.log('[WS] Attempting to reconnect...');
                        connect();
                    }, 3000);
                }
            };

            ws.current.onerror = (error) => {
                console.error('[WS] Error:', error);
                setConnectionError('WebSocket connection failed');
                onError?.('Connection error occurred');
            };

            ws.current.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    onMessage?.(data);

                    // Handle specific message types
                    if (data.type === 'workflow_update' && data.stage !== undefined) {
                        onWorkflowUpdate?.(data.stage, data.step_name || '');
                    } else if (data.type === 'pause') {
                        onPause?.(data.message || 'Workflow paused');
                    } else if (data.type === 'complete') {
                        onComplete?.();
                    }
                } catch (err) {
                    console.error('[WS] Failed to parse message:', err);
                }
            };
        } catch (err) {
            console.error('[WS] Connection error:', err);
            setConnectionError('Failed to establish connection');
        }
    }, [projectId, initialPrompt, onMessage, onWorkflowUpdate, onPause, onComplete, onError]);

    const sendMessage = useCallback((content: string) => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(
                JSON.stringify({
                    type: 'user_message',
                    content,
                })
            );
            return true;
        }
        return false;
    }, []);

    const disconnect = useCallback(() => {
        if (ws.current) {
            ws.current.close(1000, 'Component unmounting');
            ws.current = null;
        }
    }, []);

    useEffect(() => {
        connect();
        return () => {
            disconnect();
        };
    }, [connect, disconnect]);

    return {
        isConnected,
        connectionError,
        sendMessage,
        reconnect: connect,
    };
};
