import { useEffect, useCallback, useRef } from 'react';

/**
 * Keyboard shortcut definition
 */
interface KeyboardShortcut {
  /** Key combination (e.g., 'ctrl+r', 'ctrl+shift+p') */
  key: string;
  /** Handler function to execute */
  handler: () => void;
  /** Description for help/documentation */
  description?: string;
  /** Whether the shortcut is enabled */
  enabled?: boolean;
  /** Prevent default browser behavior */
  preventDefault?: boolean;
}

/**
 * Parse a key combination string into its parts
 */
const parseKeyCombo = (combo: string): { ctrl: boolean; shift: boolean; alt: boolean; meta: boolean; key: string } => {
  const parts = combo.toLowerCase().split('+');
  return {
    ctrl: parts.includes('ctrl') || parts.includes('control'),
    shift: parts.includes('shift'),
    alt: parts.includes('alt'),
    meta: parts.includes('meta') || parts.includes('cmd') || parts.includes('command'),
    key: parts.filter(p => !['ctrl', 'control', 'shift', 'alt', 'meta', 'cmd', 'command'].includes(p))[0] || '',
  };
};

/**
 * Check if a keyboard event matches a key combination
 */
const matchesKeyCombo = (event: KeyboardEvent, combo: string): boolean => {
  const parsed = parseKeyCombo(combo);
  
  return (
    event.ctrlKey === parsed.ctrl &&
    event.shiftKey === parsed.shift &&
    event.altKey === parsed.alt &&
    event.metaKey === parsed.meta &&
    event.key.toLowerCase() === parsed.key
  );
};

/**
 * useKeyboardShortcuts Hook
 * 
 * Registers keyboard shortcuts and handles their execution.
 * Shortcuts are automatically cleaned up when the component unmounts.
 * 
 * Usage:
 *   useKeyboardShortcuts([
 *     { key: 'ctrl+r', handler: runOptimizer, description: 'Run optimizer' },
 *     { key: 'ctrl+s', handler: stopOptimizer, description: 'Stop optimizer' },
 *     { key: 'ctrl+p', handler: togglePolicies, description: 'Toggle policies' },
 *   ]);
 */
const useKeyboardShortcuts = (shortcuts: KeyboardShortcut[]): void => {
  const shortcutsRef = useRef(shortcuts);
  
  // Keep shortcuts ref up to date
  useEffect(() => {
    shortcutsRef.current = shortcuts;
  }, [shortcuts]);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    // Don't trigger shortcuts when typing in input fields
    const target = event.target as HTMLElement;
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable
    ) {
      return;
    }

    for (const shortcut of shortcutsRef.current) {
      if (shortcut.enabled === false) continue;
      
      if (matchesKeyCombo(event, shortcut.key)) {
        if (shortcut.preventDefault !== false) {
          event.preventDefault();
        }
        shortcut.handler();
        return;
      }
    }
  }, []);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
};

/**
 * Get a list of all registered shortcuts for help display
 */
const getShortcutsList = (shortcuts: KeyboardShortcut[]): { key: string; description: string }[] => {
  return shortcuts
    .filter(s => s.enabled !== false && s.description)
    .map(s => ({
      key: s.key.toUpperCase(),
      description: s.description!,
    }));
};

/**
 * Format a key combination for display
 */
const formatKeyCombo = (combo: string): string => {
  return combo
    .split('+')
    .map(part => {
      switch (part.toLowerCase()) {
        case 'ctrl':
        case 'control':
          return 'Ctrl';
        case 'shift':
          return 'Shift';
        case 'alt':
          return 'Alt';
        case 'meta':
        case 'cmd':
        case 'command':
          return '⌘';
        default:
          return part.toUpperCase();
      }
    })
    .join(' + ');
};

export { useKeyboardShortcuts, getShortcutsList, formatKeyCombo };
export type { KeyboardShortcut };
export default useKeyboardShortcuts;
