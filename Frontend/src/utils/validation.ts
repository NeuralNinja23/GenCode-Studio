// frontend/src/utils/validation.ts
/**
 * Validation utilities for user input sanitization and security
 */

/**
 * Validate project ID format
 * Only allows alphanumeric characters, hyphens, and underscores
 * 
 * @param id - Project identifier to validate
 * @returns True if valid, false otherwise
 * 
 * @example
 * ```ts
 * validateProjectId('my-project-123'); // true
 * validateProjectId('../../../etc/passwd'); // false
 * validateProjectId('project@#$'); // false
 * ```
 */
export const validateProjectId = (id: string): boolean => {
    if (!id || typeof id !== 'string') return false;

    // Only allow alphanumeric, hyphens, underscores
    // Length between 1-100 characters
    return /^[a-zA-Z0-9_-]{1,100}$/.test(id);
};

/**
 * Validate file path to prevent directory traversal attacks
 * 
 * @param path - File path to validate
 * @returns True if safe, false if potentially malicious
 * 
 * @example
 * ```ts
 * validateFilePath('src/App.tsx'); // true
 * validateFilePath('../../../etc/passwd'); // false
 * validateFilePath('/etc/passwd'); // false
 * ```
 */
export const validateFilePath = (path: string): boolean => {
    if (!path || typeof path !== 'string') return false;

    // Prevent directory traversal
    if (path.includes('..')) return false;

    // Prevent absolute paths
    if (path.startsWith('/')) return false;

    // Prevent null bytes
    if (path.includes('\0')) return false;

    // Max reasonable path length
    if (path.length > 500) return false;

    return true;
};

/**
 * Sanitize user input to prevent XSS attacks
 * Removes HTML tags and dangerous characters
 * 
 * @param input - User input string
 * @returns Sanitized string
 * 
 * @example
 * ```ts
 * sanitizeInput('<script>alert("xss")</script>'); // 'scriptalert("xss")/script'
 * sanitizeInput('Hello <b>World</b>'); // 'Hello World'
 * ```
 */
export const sanitizeInput = (input: string): string => {
    if (!input || typeof input !== 'string') return '';

    // Remove HTML tags
    let sanitized = input.replace(/<[^>]*>/g, '');

    // Remove control characters except newlines and tabs
    sanitized = sanitized.replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, '');

    // Trim whitespace
    sanitized = sanitized.trim();

    return sanitized;
};

/**
 * Validate prompt length
 * 
 * @param prompt - User prompt to validate
 * @returns True if valid length, false otherwise
 */
export const validatePromptLength = (prompt: string): boolean => {
    if (!prompt || typeof prompt !== 'string') return false;

    const trimmed = prompt.trim();

    // Min 3 characters, max 5000 characters
    return trimmed.length >= 3 && trimmed.length <= 5000;
};

/**
 * Validate WebSocket URL format
 * 
 * @param url - WebSocket URL to validate
 * @returns True if valid WebSocket URL, false otherwise
 */
export const validateWebSocketUrl = (url: string): boolean => {
    if (!url || typeof url !== 'string') return false;

    try {
        const parsed = new URL(url);
        return parsed.protocol === 'ws:' || parsed.protocol === 'wss:';
    } catch {
        return false;
    }
};

/**
 * Validate HTTP URL format
 * 
 * @param url - HTTP URL to validate
 * @returns True if valid HTTP URL, false otherwise
 */
export const validateHttpUrl = (url: string): boolean => {
    if (!url || typeof url !== 'string') return false;

    try {
        const parsed = new URL(url);
        return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
        return false;
    }
};
