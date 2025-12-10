// frontend/src/config/sentry.ts
import * as Sentry from "@sentry/react";

/**
 * Initialize Sentry error tracking
 * Only initializes in production or when VITE_SENTRY_DSN is set
 * 
 * @example
 * ```typescript
 * // In main.tsx
 * import { initSentry } from './config/sentry';
 * initSentry();
 * ```
 */
export const initSentry = () => {
    const dsn = (import.meta as any).env?.VITE_SENTRY_DSN;
    const environment = (import.meta as any).env?.MODE || 'development';

    // Only initialize if DSN is provided
    if (!dsn) {
        console.log('[Sentry] No DSN provided, skipping initialization');
        return;
    }

    console.log(`[Sentry] Initializing for environment: ${environment}`);

    Sentry.init({
        dsn: dsn,
        environment: environment,

        // Performance monitoring with browser tracing
        integrations: [
            new Sentry.BrowserTracing(),
            new Sentry.Replay({
                // Mask all text and images by default for privacy
                maskAllText: true,
                blockAllMedia: true,
            }),
        ],

        // Sample rate for performance monitoring
        // 1.0 = 100% of transactions, 0.1 = 10%
        tracesSampleRate: environment === 'production' ? 0.1 : 1.0,

        // Sample rate for session replay
        replaysSessionSampleRate: 0.1, // 10% of sessions
        replaysOnErrorSampleRate: 1.0, // 100% of error sessions

        // Send default breadcrumbs for debugging
        beforeBreadcrumb(breadcrumb) {
            // Filter out noisy breadcrumbs if needed
            if (breadcrumb.category === 'console' && breadcrumb.level !== 'error') {
                return null; // Don't send non-error console logs
            }
            return breadcrumb;
        },

        // Filter events before sending
        beforeSend(event, hint) {
            // Don't send errors in development unless explicitly enabled
            if (environment === 'development' && !event.tags?.forceSend) {
                console.log('[Sentry] Blocked event in development:', event);
                return null;
            }

            // Add additional context
            if (event.exception) {
                console.log('[Sentry] Sending error:', event.exception);
            }

            return event;
        },
    });

    // Set default tags
    Sentry.setTag('app.name', 'gencode-studio');
    Sentry.setTag('app.version', '1.0.0');

    console.log('[Sentry] ✅ Initialized successfully');
};

/**
 * Export Sentry for use in components
 */
export default Sentry;

/**
 * Capture an exception to Sentry
 * @param error - Error to capture
 * @param context - Additional context
 */
export const captureException = (error: Error, context?: Record<string, any>) => {
    return Sentry.captureException(error, { extra: context });
};

/**
 * Capture a message to Sentry
 * @param message - Message to capture
 * @param level - Severity level
 */
export const captureMessage = (message: string, level: Sentry.SeverityLevel = 'info') => {
    return Sentry.captureMessage(message, level);
};

/**
 * Set user context for error tracking
 * @param user - User information
 */
export const setUser = (user: Sentry.User | null) => {
    Sentry.setUser(user);
};

/**
 * Set a tag for filtering errors
 * @param key - Tag key
 * @param value - Tag value
 */
export const setTag = (key: string, value: string) => {
    Sentry.setTag(key, value);
};
