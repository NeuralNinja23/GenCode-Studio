// frontend/src/config/env.ts
/**
 * Centralized environment variable handling
 * Single source of truth for backend URL configuration
 */

/**
 * Get backend URL from environment variables
 * Checks both Vite and React env var formats
 */
export const getBackendUrl = (): string => {
    const envUrl =
        (import.meta as any).env?.VITE_BACKEND_URL ||
        (import.meta as any).env?.REACT_APP_BACKEND_URL ||
        '';

    return envUrl;
};

/**
 * Get the base URL for the backend API
 * Falls back to current window location if not configured
 */
export const getBackendBaseUrl = (): string => {
    const backendUrl = getBackendUrl();

    if (backendUrl) {
        return backendUrl.replace(/\/$/, '');
    }

    // Fallback to current location
    return `${window.location.protocol}//${window.location.host}`;
};

/**
 * Build a complete API URL from a path
 * @param path - API path (e.g., '/api/projects')
 * @returns Complete URL
 */
export const getApiUrl = (path: string): string => {
    const base = getBackendBaseUrl();
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${base}${cleanPath}`;
};

/**
 * Get WebSocket URL for a project
 * Handles both development and production environments
 * @param projectId - Project identifier
 * @returns WebSocket URL
 */
export const getWebSocketUrl = (projectId: string): string => {
    const backendUrl = getBackendUrl();

    // If no backend URL configured, use current window location
    if (!backendUrl) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/${projectId}`;
    }

    // Parse backend URL and construct WebSocket URL
    try {
        const url = new URL(backendUrl);
        const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = url.host;
        return `${protocol}//${host}/ws/${projectId}`;
    } catch (error) {
        // Fallback if URL parsing fails
        console.error('[ENV] Failed to parse backend URL:', error);
        const wsProtocol = backendUrl.startsWith('https') ? 'wss' : 'ws';
        const host = backendUrl.replace(/^https?:\/\//, '');
        return `${wsProtocol}://${host}/ws/${projectId}`;
    }
};
