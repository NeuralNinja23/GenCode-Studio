// frontend/src/hooks/usePreview.ts
import { useState, useCallback, useEffect } from 'react';

export interface FilePayload {
  path: string;
  code: string;
}

export type BundlerStatus = 'connected' | 'bundling' | 'error' | 'disconnected'; // Simplified status for the preview panel

// This is the payload structure the backend expects
export interface BundleRequestPayload {
  files: FilePayload[];
  projectId: string;
}

// 👈 The hook no longer handles WebSocket connection logic
export const usePreviewWS = (socket: WebSocket | null) => {
  const [html, setHtml] = useState('');
  const [error, setError] = useState('');
  const [status, setStatus] = useState<BundlerStatus>('connected'); // Assume connected if main WS is open
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Effect to listen for PREVIEW_READY message on the passed-in socket
  useEffect(() => {
    if (!socket) {
        setStatus('disconnected');
        return;
    }
    
    // Clear state on successful connection/socket availability
    setStatus('connected');
    
    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'PREVIEW_READY': // Backend sends this with the Vite URL
            console.log('[usePreviewWS] Preview URL received:', data.url);
            setPreviewUrl(data.url);
            setHtml('');
            setError('');
            setStatus('connected');
            break;
            
          case 'BUNDLE_RESULT': // Backend uses this for build errors
            if (data.success === false) {
              console.error('[usePreviewWS] Bundle Error:', data.error);
              setError(data.error || 'Preview server failed to start.');
              setStatus('error');
              setPreviewUrl(null);
            }
            break;

          case 'WORKFLOW_UPDATE':
             // Transition status on starting the preview process
             if (data.status?.includes('Starting preview server')) {
               setStatus('bundling');
               setPreviewUrl(null);
               setError('');
             }
            break;

          // New unified backend message: { type: 'BUNDLE_RESPONSE', payload: { status, url, error, projectId } }
          case 'BUNDLE_RESPONSE': {
            const payload = data.payload || {};
            if (payload.status === 'ready' && payload.url) {
              console.log('[usePreviewWS] Preview URL ready:', payload.url);
              setPreviewUrl(payload.url);
              setHtml('');
              setError('');
              setStatus('connected');
            } else if (payload.status === 'error') {
              console.error('[usePreviewWS] Bundle error:', payload.error);
              setError(payload.error || 'Preview server failed to start.');
              setStatus('error');
              setPreviewUrl(null);
            }
            break;
          }
            
          default:
            break;
        }
      } catch (e) {
        // console.warn('[usePreviewWS] Error parsing message:', e);
      }
    };

    socket.addEventListener('message', handleMessage);
    return () => socket.removeEventListener('message', handleMessage);
  }, [socket]); // Dependency on the passed-in socket

  // Function to request bundling/server start
  const requestBundle = useCallback(async (payload: BundleRequestPayload) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setError('Cannot start preview: Server connection is closed.');
      setStatus('disconnected');
      return;
    }

    console.log(`[usePreviewWS] Sending BUNDLE_REQUEST for ${payload.projectId}`);
    setStatus('bundling');
    setError('');
    setPreviewUrl(null); 
    
    // Send the correct message structure
    socket.send(JSON.stringify({
      type: 'BUNDLE_REQUEST',
      payload: {
        projectId: payload.projectId,
        files: payload.files 
      }
    }));
  }, [socket]); // Dependency on the passed-in socket

  return { html, error, status, requestBundle, previewUrl };
};