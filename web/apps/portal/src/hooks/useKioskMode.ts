/**
 * Kiosk Mode Hook for PlannedEducation
 * Implements browser-based lockdown for exam taking on air-gapped networks.
 * 
 * Features:
 * - Fullscreen enforcement with auto-recovery
 * - Keyboard shortcut blocking (Alt+Tab, Win, Ctrl+Esc, etc.)
 * - Context menu / right-click blocking
 * - DevTools detection and deterrence
 * - Tab/window focus loss detection
 * - Navigation blocking (beforeunload)
 * - Copy/paste/drag blocking
 * - Print/screenshot blocking
 * - Mobile gesture blocking
 * - Visibility change handling
 * 
 * NOTE: Browser-based kiosk mode cannot be 100% secure against determined attackers.
 * For maximum security, use Safe Exam Browser (SEB) native client.
 * This provides a strong deterrent for typical students on managed devices.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useToast } from '../contexts/ToastContext';

interface KioskModeOptions {
  /** Enable kiosk mode (default: true) */
  enabled?: boolean;
  /** Callback when security violation detected */
  onViolation?: (type: KioskViolationType, details?: string) => void;
  /** Callback when exam should be terminated due to critical violation */
  onCriticalViolation?: (reason: string) => void;
  /** Allow exiting fullscreen via Escape key (for accessibility) */
  allowEscapeExit?: boolean;
  /** Custom message for beforeunload */
  beforeUnloadMessage?: string;
}

export type KioskViolationType = 
  | 'fullscreen_exit'
  | 'focus_loss'
  | 'tab_switch'
  | 'shortcut_blocked'
  | 'context_menu_blocked'
  | 'devtools_detected'
  | 'navigation_blocked'
  | 'copy_paste_blocked'
  | 'print_blocked'
  | 'mobile_gesture_blocked';

interface KioskViolation {
  type: KioskViolationType;
  timestamp: number;
  details?: string;
  userAgent?: string;
}

export function useKioskMode({
  enabled = true,
  onViolation,
  onCriticalViolation,
  allowEscapeExit = false,
  beforeUnloadMessage = 'Leaving this page will terminate your exam. Are you sure?',
}: KioskModeOptions = {}) {
  const { warn: showWarn } = useToast();
  const violationsRef = useRef<KioskViolation[]>([]);
  const isFullscreenRef = useRef(false);
  const devToolsDetectedRef = useRef(false);
  const fullscreenCheckIntervalRef = useRef<number | null>(null);
  const devToolsCheckIntervalRef = useRef<number | null>(null);
  const [isActive, setIsActive] = useState(false);

  // Record violation
  const recordViolation = useCallback((type: KioskViolationType, details?: string) => {
    const violation: KioskViolation = {
      type,
      timestamp: Date.now(),
      details,
      userAgent: navigator.userAgent,
    };
    violationsRef.current.push(violation);
    
    // Call callback
    onViolation?.(type, details);
    
    // Show warning to user
    const messages: Record<KioskViolationType, string> = {
      fullscreen_exit: 'Fullscreen mode exited. Exam may be terminated.',
      focus_loss: 'Window focus lost. Please return to the exam immediately.',
      tab_switch: 'Tab switching detected. Exam may be terminated.',
      shortcut_blocked: 'Keyboard shortcut blocked.',
      context_menu_blocked: 'Right-click/context menu is disabled during exam.',
      devtools_detected: 'Developer tools detected. Exam may be terminated.',
      navigation_blocked: 'Navigation away from exam is not allowed.',
      copy_paste_blocked: 'Copy/paste is disabled during exam.',
      print_blocked: 'Printing is disabled during exam.',
      mobile_gesture_blocked: 'Gestures are disabled during exam.',
    };
    showWarn(messages[type] || `Security violation: ${type}`);
  }, [onViolation, showWarn]);

  // Enter fullscreen
  const enterFullscreen = useCallback(async () => {
    if (!enabled) return;
    
    try {
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        await elem.requestFullscreen({ navigationUI: 'hide' });
      } else if ((elem as any).webkitRequestFullscreen) {
        await (elem as any).webkitRequestFullscreen((Element as any).ALLOW_KEYBOARD_INPUT);
      } else if ((elem as any).msRequestFullscreen) {
        await (elem as any).msRequestFullscreen();
      }
      isFullscreenRef.current = true;
    } catch (err) {
      console.warn('Failed to enter fullscreen:', err);
      // Some browsers require user gesture - will retry on first interaction
    }
  }, [enabled]);

  // Exit fullscreen (for cleanup)
  const exitFullscreen = useCallback(async () => {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else if ((document as any).webkitExitFullscreen) {
        await (document as any).webkitExitFullscreen();
      } else if ((document as any).msExitFullscreen) {
        await (document as any).msExitFullscreen();
      }
      isFullscreenRef.current = false;
    } catch (err) {
      console.warn('Failed to exit fullscreen:', err);
    }
  }, []);

  // Handle fullscreen change
  const handleFullscreenChange = useCallback(() => {
    if (!enabled) return;
    
    const isNowFullscreen = !!(
      document.fullscreenElement ||
      (document as any).webkitFullscreenElement ||
      (document as any).msFullscreenElement
    );
    
    if (isFullscreenRef.current && !isNowFullscreen) {
      // Fullscreen was exited unexpectedly
      recordViolation('fullscreen_exit', 'User exited fullscreen mode');
      
      // Try to re-enter fullscreen after a brief delay
      setTimeout(() => {
        if (enabled && !document.fullscreenElement) {
          enterFullscreen();
        }
      }, 1000);
    }
    
    isFullscreenRef.current = isNowFullscreen;
  }, [enabled, recordViolation, enterFullscreen]);

  // Block keyboard shortcuts
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!enabled) return;
    
    const blockedShortcuts: Array<{ keys: string[]; description: string }> = [
      // Task switching
      { keys: ['Alt', 'Tab'], description: 'Alt+Tab (task switch)' },
      { keys: ['Alt', 'Shift', 'Tab'], description: 'Alt+Shift+Tab (reverse task switch)' },
      { keys: ['Meta', 'Tab'], description: 'Cmd+Tab (macOS task switch)' },
      { keys: ['Meta', 'Shift', 'Tab'], description: 'Cmd+Shift+Tab (macOS reverse task switch)' },
      
      // System shortcuts
      { keys: ['Control', 'Escape'], description: 'Ctrl+Esc (Start menu)' },
      { keys: ['Meta'], description: 'Windows/Command key' },
      { keys: ['Meta', 'Shift', 'Escape'], description: 'Ctrl+Shift+Esc (Task Manager)' },
      { keys: ['Control', 'Shift', 'Escape'], description: 'Ctrl+Shift+Esc (Task Manager)' },
      { keys: ['Control', 'Alt', 'Delete'], description: 'Ctrl+Alt+Del (Security screen)' },
      
      // Window management
      { keys: ['Meta', 'D'], description: 'Win+D (Show desktop)' },
      { keys: ['Meta', 'M'], description: 'Win+M (Minimize all)' },
      { keys: ['Meta', 'Shift', 'M'], description: 'Win+Shift+M (Restore minimized)' },
      { keys: ['Meta', 'Up'], description: 'Win+Up (Maximize)' },
      { keys: ['Meta', 'Down'], description: 'Win+Down (Minimize/Restore)' },
      { keys: ['Meta', 'Left'], description: 'Win+Left (Snap left)' },
      { keys: ['Meta', 'Right'], description: 'Win+Right (Snap right)' },
      
      // Browser shortcuts
      { keys: ['Control', 'T'], description: 'Ctrl+T (New tab)' },
      { keys: ['Control', 'N'], description: 'Ctrl+N (New window)' },
      { keys: ['Control', 'Shift', 'N'], description: 'Ctrl+Shift+N (Incognito)' },
      { keys: ['Control', 'W'], description: 'Ctrl+W (Close tab)' },
      { keys: ['Control', 'Shift', 'W'], description: 'Ctrl+Shift+W (Close window)' },
      { keys: ['Control', 'Shift', 'T'], description: 'Ctrl+Shift+T (Reopen tab)' },
      { keys: ['Control', 'Tab'], description: 'Ctrl+Tab (Next tab)' },
      { keys: ['Control', 'Shift', 'Tab'], description: 'Ctrl+Shift+Tab (Prev tab)' },
      { keys: ['Control', 'L'], description: 'Ctrl+L (Address bar)' },
      { keys: ['Control', 'R'], description: 'Ctrl+R (Reload)' },
      { keys: ['Control', 'Shift', 'R'], description: 'Ctrl+Shift+R (Hard reload)' },
      { keys: ['F5'], description: 'F5 (Reload)' },
      { keys: ['Control', 'F5'], description: 'Ctrl+F5 (Hard reload)' },
      
      // Developer tools
      { keys: ['F12'], description: 'F12 (DevTools)' },
      { keys: ['Control', 'Shift', 'I'], description: 'Ctrl+Shift+I (DevTools)' },
      { keys: ['Control', 'Shift', 'J'], description: 'Ctrl+Shift+J (Console)' },
      { keys: ['Control', 'Shift', 'C'], description: 'Ctrl+Shift+C (Inspect)' },
      { keys: ['Meta', 'Option', 'I'], description: 'Cmd+Opt+I (macOS DevTools)' },
      { keys: ['Meta', 'Option', 'J'], description: 'Cmd+Opt+J (macOS Console)' },
      { keys: ['Meta', 'Option', 'C'], description: 'Cmd+Opt+C (macOS Inspect)' },
      
      // Other
      { keys: ['Control', 'P'], description: 'Ctrl+P (Print)' },
      { keys: ['Control', 'S'], description: 'Ctrl+S (Save)' },
      { keys: ['Control', 'A'], description: 'Ctrl+A (Select all)' },
      { keys: ['Control', 'C'], description: 'Ctrl+C (Copy)' },
      { keys: ['Control', 'V'], description: 'Ctrl+V (Paste)' },
      { keys: ['Control', 'X'], description: 'Ctrl+X (Cut)' },
      { keys: ['Control', 'U'], description: 'Ctrl+U (View source)' },
      { keys: ['Control', 'Shift', 'U'], description: 'Ctrl+Shift+U (View source)' },
      { keys: ['Meta', 'U'], description: 'Cmd+U (macOS View source)' },
    ];
    
    // Check if current key combination matches any blocked shortcut
    const pressedKeys: string[] = [];
    if (e.ctrlKey) pressedKeys.push('Control');
    if (e.metaKey) pressedKeys.push('Meta');
    if (e.altKey) pressedKeys.push('Alt');
    if (e.shiftKey) pressedKeys.push('Shift');
    if (e.key && e.key !== 'Control' && e.key !== 'Meta' && e.key !== 'Alt' && e.key !== 'Shift') {
      pressedKeys.push(e.key);
    }
    
    for (const shortcut of blockedShortcuts) {
      if (shortcut.keys.length === pressedKeys.length &&
          shortcut.keys.every(k => pressedKeys.includes(k))) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        recordViolation('shortcut_blocked', shortcut.description);
        return false;
      }
    }
    
    // Allow Escape to exit fullscreen if configured
    if (e.key === 'Escape' && allowEscapeExit && isFullscreenRef.current) {
      exitFullscreen();
    }
    
    return true;
  }, [enabled, allowEscapeExit, recordViolation, exitFullscreen]);

  // Block context menu (right-click)
  const handleContextMenu = useCallback((e: MouseEvent) => {
    if (!enabled) return;
    e.preventDefault();
    e.stopPropagation();
    recordViolation('context_menu_blocked', 'Right-click/context menu blocked');
    return false;
  }, [enabled, recordViolation]);

  // Block copy/paste/cut/drag
  const handleCopyPaste = useCallback((e: ClipboardEvent | DragEvent) => {
    if (!enabled) return;
    e.preventDefault();
    e.stopPropagation();
    recordViolation('copy_paste_blocked', e.type);
    return false;
  }, [enabled, recordViolation]);

  // Block print
  const handleBeforePrint = useCallback((e: Event) => {
    if (!enabled) return;
    e.preventDefault();
    recordViolation('print_blocked', 'Print dialog blocked');
    return false;
  }, [enabled, recordViolation]);

  // Block navigation (beforeunload)
  const handleBeforeUnload = useCallback((e: BeforeUnloadEvent) => {
    if (!enabled) return;
    e.preventDefault();
    e.returnValue = beforeUnloadMessage;
    recordViolation('navigation_blocked', 'Page unload attempted');
    return beforeUnloadMessage;
  }, [enabled, beforeUnloadMessage, recordViolation]);

  // Handle visibility change (tab switching)
  const handleVisibilityChange = useCallback(() => {
    if (!enabled) return;
    
    if (document.hidden) {
      recordViolation('tab_switch', 'Tab hidden / switched away');
      
      // Check if we should terminate exam on tab switch
      // For now, just warn - could be configured to terminate
    } else {
      // Tab became visible again - check if we're still in fullscreen
      if (isFullscreenRef.current && !document.fullscreenElement) {
        recordViolation('fullscreen_exit', 'Fullscreen lost while tab was hidden');
        setTimeout(() => enterFullscreen(), 500);
      }
    }
  }, [enabled, recordViolation, enterFullscreen]);

  // Handle focus/blur (window focus loss)
  const handleFocusChange = useCallback((e: FocusEvent) => {
    if (!enabled) return;
    
    if (e.type === 'blur') {
      recordViolation('focus_loss', 'Window lost focus');
    }
  }, [enabled, recordViolation]);

  // DevTools detection
  const checkDevTools = useCallback(() => {
    if (!enabled) return;
    
    // Method 1: Window size difference (DevTools docked)
    const threshold = 160;
    const widthDiff = window.outerWidth - window.innerWidth;
    const heightDiff = window.outerHeight - window.innerHeight;
    
    // Method 2: Console timing (DevTools open affects performance)
    const start = performance.now();
    debugger; // This line causes a pause if DevTools is open
    const end = performance.now();
    
    const devToolsOpen = 
      widthDiff > threshold || 
      heightDiff > threshold || 
      (end - start) > 100;
    
    if (devToolsOpen && !devToolsDetectedRef.current) {
      devToolsDetectedRef.current = true;
      recordViolation('devtools_detected', 'Developer tools opened');
      onCriticalViolation?.('Developer tools detected - exam terminated for security');
    } else if (!devToolsOpen) {
      devToolsDetectedRef.current = false;
    }
  }, [enabled, recordViolation, onCriticalViolation]);

  // Mobile gesture blocking
  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (!enabled) return;
    // Block multi-touch gestures (pinch zoom, swipe navigation)
    if (e.touches.length > 1) {
      e.preventDefault();
      recordViolation('mobile_gesture_blocked', 'Multi-touch gesture blocked');
    }
  }, [enabled, recordViolation]);

  const handleGestureStart = useCallback((e: Event) => {
    if (!enabled) return;
    e.preventDefault();
    recordViolation('mobile_gesture_blocked', 'Touch gesture blocked');
    return false;
  }, [enabled, recordViolation]);

  // Disable text selection
  const handleSelectStart = useCallback((e: Event) => {
    if (!enabled) return;
    // Allow selection in input/textarea elements
    const target = e.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
      return true;
    }
    e.preventDefault();
    return false;
  }, [enabled]);

  // Initialize kiosk mode
  useEffect(() => {
    if (!enabled) return;
    
    setIsActive(true);
    
    // Enter fullscreen on first user interaction
    const handleFirstInteraction = () => {
      enterFullscreen();
      document.removeEventListener('click', handleFirstInteraction);
      document.removeEventListener('keydown', handleFirstInteraction);
    };
    document.addEventListener('click', handleFirstInteraction, { once: true });
    document.addEventListener('keydown', handleFirstInteraction, { once: true });
    
    // Event listeners
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('msfullscreenchange', handleFullscreenChange);
    document.addEventListener('keydown', handleKeyDown, true); // Use capture phase
    document.addEventListener('contextmenu', handleContextMenu, true);
    document.addEventListener('copy', handleCopyPaste, true);
    document.addEventListener('cut', handleCopyPaste, true);
    document.addEventListener('paste', handleCopyPaste, true);
    document.addEventListener('dragstart', handleCopyPaste, true);
    document.addEventListener('drop', handleCopyPaste, true);
    window.addEventListener('beforeprint', handleBeforePrint);
    window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleFocusChange);
    window.addEventListener('focus', handleFocusChange);
    document.addEventListener('touchmove', handleTouchMove, { passive: false });
    document.addEventListener('gesturestart', handleGestureStart, { passive: false });
    document.addEventListener('selectstart', handleSelectStart, true);
    
    // Start DevTools detection interval
    devToolsCheckIntervalRef.current = window.setInterval(checkDevTools, 1000);
    
    // Start fullscreen monitoring interval (backup)
    fullscreenCheckIntervalRef.current = window.setInterval(() => {
      if (enabled && isFullscreenRef.current && !document.fullscreenElement) {
        handleFullscreenChange();
      }
    }, 500);
    
    // Disable text selection via CSS
    document.body.style.userSelect = 'none';
    document.body.style.webkitUserSelect = 'none';
    (document.body.style as any).msUserSelect = 'none';
    (document.body.style as any).mozUserSelect = 'none';
    
    // Prevent zoom on mobile
    document.body.style.touchAction = 'none';
    
    return () => {
      // Cleanup
      setIsActive(false);
      document.removeEventListener('click', handleFirstInteraction);
      document.removeEventListener('keydown', handleFirstInteraction);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('msfullscreenchange', handleFullscreenChange);
      document.removeEventListener('keydown', handleKeyDown, true);
      document.removeEventListener('contextmenu', handleContextMenu, true);
      document.removeEventListener('copy', handleCopyPaste, true);
      document.removeEventListener('cut', handleCopyPaste, true);
      document.removeEventListener('paste', handleCopyPaste, true);
      document.removeEventListener('dragstart', handleCopyPaste, true);
      document.removeEventListener('drop', handleCopyPaste, true);
      window.removeEventListener('beforeprint', handleBeforePrint);
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleFocusChange);
      window.removeEventListener('focus', handleFocusChange);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('gesturestart', handleGestureStart);
      document.removeEventListener('selectstart', handleSelectStart, true);
      
      if (devToolsCheckIntervalRef.current) {
        clearInterval(devToolsCheckIntervalRef.current);
      }
      if (fullscreenCheckIntervalRef.current) {
        clearInterval(fullscreenCheckIntervalRef.current);
      }
      
      // Restore styles
      document.body.style.userSelect = '';
      document.body.style.webkitUserSelect = '';
      (document.body.style as any).msUserSelect = '';
      (document.body.style as any).mozUserSelect = '';
      document.body.style.touchAction = '';
      
      // Exit fullscreen on cleanup
      exitFullscreen();
    };
  }, [
    enabled,
    enterFullscreen,
    exitFullscreen,
    handleFullscreenChange,
    handleKeyDown,
    handleContextMenu,
    handleCopyPaste,
    handleBeforePrint,
    handleBeforeUnload,
    handleVisibilityChange,
    handleFocusChange,
    checkDevTools,
    handleTouchMove,
    handleGestureStart,
    handleSelectStart,
  ]);

  // Get violations for reporting
  const getViolations = useCallback(() => {
    return [...violationsRef.current];
  }, []);

  // Clear violations
  const clearViolations = useCallback(() => {
    violationsRef.current = [];
  }, []);

  return {
    isActive,
    enterFullscreen,
    exitFullscreen,
    getViolations,
    clearViolations,
    violationsCount: violationsRef.current.length,
  };
}

export default useKioskMode;