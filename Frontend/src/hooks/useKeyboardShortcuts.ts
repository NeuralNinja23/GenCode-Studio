import { useEffect, useCallback } from 'react';

interface KeyboardShortcut {
    key: string;
    ctrlKey?: boolean;
    metaKey?: boolean;
    shiftKey?: boolean;
    altKey?: boolean;
    callback: (event: KeyboardEvent) => void;
    description?: string;
}

/**
 * Custom hook for managing keyboard shortcuts
 * 
 * @example
 * ```tsx
 * useKeyboardShortcuts([
 *   {
 *     key: 'Enter',
 *     ctrlKey: true,
 *     callback: () => sendMessage(),
 *     description: 'Send message'
 *   }
 * ]);
 * ```
 */
export const useKeyboardShortcuts = (shortcuts: KeyboardShortcut[]) => {
    const handleKeyDown = useCallback((event: KeyboardEvent) => {
        shortcuts.forEach((shortcut) => {
            const matchesKey = event.key === shortcut.key;
            const matchesCtrl = shortcut.ctrlKey ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey;
            const matchesShift = shortcut.shiftKey ? event.shiftKey : !event.shiftKey;
            const matchesAlt = shortcut.altKey ? event.altKey : !event.altKey;

            if (matchesKey && matchesCtrl && matchesShift && matchesAlt) {
                event.preventDefault();
                shortcut.callback(event);
            }
        });
    }, [shortcuts]);

    useEffect(() => {
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);

    return shortcuts;
};
