// frontend/src/utils/retry.ts
/**
 * Retry utilities for resilient network operations
 */

/**
 * Configuration for retry behavior
 */
export interface RetryConfig {
    /** Maximum number of attempts (including initial try) */
    maxAttempts: number;
    /** Initial delay in milliseconds */
    delayMs: number;
    /** Multiplier for exponential backoff */
    backoffMultiplier: number;
    /** Maximum delay cap in milliseconds */
    maxDelayMs?: number;
    /** Function to determine if error should be retried */
    shouldRetry?: (error: any) => boolean;
    /** Callback for each retry attempt */
    onRetry?: (attempt: number, error: any) => void;
}

/**
 * Default retry configuration
 */
const DEFAULT_RETRY_CONFIG: RetryConfig = {
    maxAttempts: 3,
    delayMs: 1000,
    backoffMultiplier: 2,
    maxDelayMs: 30000, // 30 seconds max
};

/**
 * Execute a function with automatic retry on failure
 * 
 * Uses exponential backoff strategy for retries.
 * 
 * @template T - Return type of the function
 * @param fn - Async function to execute
 * @param config - Retry configuration
 * @returns Promise resolving to function result
 * @throws Last error if all retries fail
 * 
 * @example
 * ```ts
 * const data = await withRetry(
 *   () => fetchData(),
 *   { maxAttempts: 3, delayMs: 1000 }
 * );
 * ```
 */
export async function withRetry<T>(
    fn: () => Promise<T>,
    config: Partial<RetryConfig> = {}
): Promise<T> {
    const finalConfig: RetryConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= finalConfig.maxAttempts; attempt++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error as Error;

            // Check if we should retry this error
            if (finalConfig.shouldRetry && !finalConfig.shouldRetry(error)) {
                throw error;
            }

            // If this was the last attempt, throw the error
            if (attempt === finalConfig.maxAttempts) {
                console.error(`[Retry] All ${finalConfig.maxAttempts} attempts failed`);
                throw lastError;
            }

            // Calculate delay with exponential backoff
            let delay = finalConfig.delayMs * Math.pow(
                finalConfig.backoffMultiplier,
                attempt - 1
            );

            // Cap at maximum delay
            if (finalConfig.maxDelayMs) {
                delay = Math.min(delay, finalConfig.maxDelayMs);
            }

            console.log(
                `[Retry] Attempt ${attempt}/${finalConfig.maxAttempts} failed, ` +
                `retrying in ${delay}ms...`,
                error
            );

            // Call retry callback if provided
            finalConfig.onRetry?.(attempt, error);

            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }

    // Should never reach here, but TypeScript needs this
    throw lastError!;
}

/**
 * Predefined retry configurations for common scenarios
 */
export const RetryPresets = {
    /** Quick retry for fast operations (3 attempts, 500ms delay) */
    QUICK: {
        maxAttempts: 3,
        delayMs: 500,
        backoffMultiplier: 2,
    } as RetryConfig,

    /** Standard retry for normal operations (3 attempts, 1s delay) */
    STANDARD: {
        maxAttempts: 3,
        delayMs: 1000,
        backoffMultiplier: 2,
    } as RetryConfig,

    /** Patient retry for slow operations (5 attempts, 2s delay) */
    PATIENT: {
        maxAttempts: 5,
        delayMs: 2000,
        backoffMultiplier: 2,
        maxDelayMs: 30000,
    } as RetryConfig,

    /** Aggressive retry for critical operations (10 attempts, 500ms delay) */
    AGGRESSIVE: {
        maxAttempts: 10,
        delayMs: 500,
        backoffMultiplier: 1.5,
        maxDelayMs: 10000,
    } as RetryConfig,
};

/**
 * Retry only on network errors, not on client/validation errors
 */
export function isNetworkError(error: any): boolean {
    if (!error) return false;

    // Axios network errors
    if (error.code === 'ECONNABORTED' || error.code === 'ECONNREFUSED') {
        return true;
    }

    // Timeout errors
    if (error.message?.includes('timeout')) {
        return true;
    }

    // 5xx server errors (retry-able)
    if (error.response?.status >= 500) {
        return true;
    }

    // Network errors
    if (error.message?.includes('Network Error')) {
        return true;
    }

    // Don't retry 4xx client errors (bad request, unauthorized, etc.)
    if (error.response?.status >= 400 && error.response?.status < 500) {
        return false;
    }

    return false;
}

/**
 * Debounce function execution
 * 
 * @param func - Function to debounce
 * @param waitMs - Delay in milliseconds
 * @returns Debounced function
 * 
 * @example
 * ```ts
 * const debouncedSearch = debounce(searchFunction, 300);
 * // searchFunction will only be called once, 300ms after last invocation
 * ```
 */
export function debounce<T extends (...args: any[]) => any>(
    func: T,
    waitMs: number
): (...args: Parameters<T>) => void {
    let timeout: ReturnType<typeof setTimeout> | null = null;

    return (...args: Parameters<T>) => {
        if (timeout) {
            clearTimeout(timeout);
        }

        timeout = setTimeout(() => {
            func(...args);
        }, waitMs);
    };
}

/**
 * Throttle function execution
 * 
 * @param func - Function to throttle
 * @param limitMs - Minimum time between calls in milliseconds
 * @returns Throttled function
 * 
 * @example
 * ```ts
 * const throttledScroll = throttle(handleScroll, 100);
 * // handleScroll will be called at most once every 100ms
 * ```
 */
export function throttle<T extends (...args: any[]) => any>(
    func: T,
    limitMs: number
): (...args: Parameters<T>) => void {
    let inThrottle: boolean = false;

    return (...args: Parameters<T>) => {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => {
                inThrottle = false;
            }, limitMs);
        }
    };
}
