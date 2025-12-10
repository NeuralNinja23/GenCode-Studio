// frontend/src/config/constants.ts
/**
 * Centralized constants for the application
 */

/**
 * API timeout values (in milliseconds)
 */
export const TIMEOUTS = {
    /** Timeout for workflow start/resume operations */
    WORKFLOW: 30000,
    /** Timeout for file listing operations */
    FILE_LIST: 10000,
    /** Timeout for file read operations */
    FILE_READ: 10000,
    /** Timeout for file save operations */
    FILE_SAVE: 15000,
    /** Timeout for connection test */
    CONNECTION_TEST: 5000,
} as const;

/**
 * WebSocket configuration
 */
export const WS_CONFIG = {
    /** Reconnection delay in milliseconds */
    RECONNECT_DELAY: 3000,
    /** Maximum reconnection attempts */
    MAX_RECONNECT_ATTEMPTS: 5,
} as const;

/**
 * UI Constants
 */
export const UI = {
    /** Debounce delay for file tree refresh */
    FILE_TREE_DEBOUNCE: 500,
    /** Auto-save delay for code editor */
    AUTO_SAVE_DELAY: 2000,
} as const;
