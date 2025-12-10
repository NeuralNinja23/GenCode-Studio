// frontend/src/components/ErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
    onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
    hasError: boolean;
    error?: Error;
    errorInfo?: ErrorInfo;
}

/**
 * Error Boundary component that catches JavaScript errors anywhere in the child component tree.
 * 
 * Prevents the entire app from crashing and shows a fallback UI instead.
 * Automatically logs errors to console and can integrate with error tracking services.
 * 
 * @example
 * ```tsx
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 */
class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
        };
    }

    static getDerivedStateFromError(error: Error): State {
        // Update state so the next render shows the fallback UI
        return {
            hasError: true,
            error,
        };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        // Log error details
        console.error('[ErrorBoundary] Caught error:', error);
        console.error('[ErrorBoundary] Error info:', errorInfo);

        // Store error info in state
        this.setState({
            errorInfo,
        });

        // Call optional error handler
        this.props.onError?.(error, errorInfo);

        // TODO: Send to error tracking service (Sentry)
        if (window.Sentry) {
            window.Sentry.captureException(error, {
                contexts: {
                    react: {
                        componentStack: errorInfo.componentStack,
                    },
                },
            });
        }
    }

    handleReset = () => {
        this.setState({
            hasError: false,
            error: undefined,
            errorInfo: undefined,
        });
    };

    render() {
        if (this.state.hasError) {
            // Custom fallback UI or default
            if (this.props.fallback) {
                return this.props.fallback;
            }

            // Default fallback UI
            return (
                <div className="flex min-h-screen flex-col items-center justify-center bg-[#0A0A0A] p-8">
                    <div className="w-full max-w-md rounded-2xl border border-red-500/20 bg-red-950/20 p-8 backdrop-blur-sm">
                        {/* Error Icon */}
                        <div className="mb-6 flex justify-center">
                            <div className="rounded-full bg-red-500/10 p-4">
                                <svg
                                    className="h-12 w-12 text-red-500"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                                    />
                                </svg>
                            </div>
                        </div>

                        {/* Error Title */}
                        <h1 className="mb-3 text-center text-xl font-bold text-white">
                            😞 Something went wrong
                        </h1>

                        {/* Error Message */}
                        <p className="mb-6 text-center text-sm text-zinc-400">
                            {this.state.error?.message || 'An unexpected error occurred'}
                        </p>

                        {/* Error Details (Development only) */}
                        {import.meta.env.DEV && this.state.errorInfo && (
                            <details className="mb-6 rounded-lg bg-black/30 p-4">
                                <summary className="cursor-pointer text-xs font-medium text-zinc-300">
                                    Error Details (Dev Mode)
                                </summary>
                                <pre className="mt-3 overflow-auto text-xs text-red-300">
                                    {this.state.error?.stack}
                                </pre>
                                <pre className="mt-2 overflow-auto text-xs text-zinc-500">
                                    {this.state.errorInfo.componentStack}
                                </pre>
                            </details>
                        )}

                        {/* Actions */}
                        <div className="flex gap-3">
                            <button
                                onClick={this.handleReset}
                                className="flex-1 rounded-lg bg-white/10 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-white/20"
                            >
                                Try Again
                            </button>
                            <button
                                onClick={() => window.location.reload()}
                                className="flex-1 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-red-500"
                            >
                                Reload Page
                            </button>
                        </div>

                        {/* Support Link */}
                        <p className="mt-6 text-center text-xs text-zinc-600">
                            If this persists, please{' '}
                            <a
                                href="https://github.com/your-repo/issues"
                                className="text-red-400 hover:text-red-300"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                report this issue
                            </a>
                        </p>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;

// Type declarations for window.Sentry
declare global {
    interface Window {
        Sentry?: {
            captureException: (error: Error, context?: any) => void;
        };
    }
}
