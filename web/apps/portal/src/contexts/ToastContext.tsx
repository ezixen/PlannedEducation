import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

// ── Toast Constants (exported separately to avoid fast-refresh warnings) ──────
export const TOAST_NOTE_HOLD_MS = 1000
export const TOAST_MEDIUM_HOLD_MS = 5000
export const TOAST_FADE_MS = 3000
const DEDUP_MS = 900

export type ToastKind = 'info' | 'success' | 'warn' | 'error'

export type ToastOptions = {
  sticky?: boolean
  key?: string
  holdMs?: number
}

type ToastItem = {
  id: string
  kind: ToastKind
  message: string
  exiting: boolean
  sticky: boolean
  key?: string
}

type ToastApi = {
  push: (kind: ToastKind, message: string, opts?: ToastOptions) => void
  info: (message: string, opts?: ToastOptions) => void
  success: (message: string, opts?: ToastOptions) => void
  warn: (message: string, opts?: ToastOptions) => void
  error: (message: string, opts?: ToastOptions) => void
  dismissKey: (key: string) => void
}

const ToastContext = createContext<ToastApi | null>(null)

let globalApi: ToastApi | null = null

function nextId(): string {
  return `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function isStickyDefault(kind: ToastKind, opts?: ToastOptions): boolean {
  if (opts?.sticky != null) return opts.sticky
  return kind === 'error' || kind === 'warn'
}

function holdMsFor(kind: ToastKind, opts?: ToastOptions): number {
  if (opts?.holdMs != null && Number.isFinite(opts.holdMs)) return Math.max(0, opts.holdMs)
  if (kind === 'success') return TOAST_NOTE_HOLD_MS
  return TOAST_MEDIUM_HOLD_MS
}

/** Imperative toast API — safe to call outside React when the provider is mounted. */
export const toast: ToastApi = {
  push(kind, message, opts) {
    const text = message.trim()
    if (!text) return
    globalApi?.push(kind, text, opts)
  },
  info(message, opts) {
    toast.push('info', message, opts)
  },
  success(message, opts) {
    toast.push('success', message, opts)
  },
  warn(message, opts) {
    toast.push('warn', message, opts)
  },
  error(message, opts) {
    toast.push('error', message, opts)
  },
  dismissKey(key) {
    globalApi?.dismissKey(key)
  },
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast requires ToastProvider')
  return ctx
}

/** Settings-style feedback helpers: empty string clears nothing (toasts dismiss themselves). */
export function notifyOk(message: string): void {
  toast.success(message)
}

export function notifyNote(message: string): void {
  toast.info(message)
}

export function notifyWarn(message: string): void {
  toast.warn(message)
}

export function notifyError(message: string): void {
  toast.error(message)
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const timersRef = useRef<Map<string, number>>(new Map())
  const fadeTimersRef = useRef<Map<string, number>>(new Map())
  const lastPushRef = useRef<{ kind: ToastKind; message: string; at: number } | null>(null)
  const itemsRef = useRef<ToastItem[]>([])
  itemsRef.current = items

  const clearAutoTimer = useCallback((id: string) => {
    const timer = timersRef.current.get(id)
    if (timer) {
      window.clearTimeout(timer)
      timersRef.current.delete(id)
    }
  }, [])

  const clearFadeTimer = useCallback((id: string) => {
    const timer = fadeTimersRef.current.get(id)
    if (timer) {
      window.clearTimeout(timer)
      fadeTimersRef.current.delete(id)
    }
  }, [])

  const dismiss = useCallback(
    (id: string) => {
      clearAutoTimer(id)
      setItems((prev) => {
        const found = prev.find((t) => t.id === id)
        if (!found || found.exiting) return prev
        return prev.map((t) => (t.id === id ? { ...t, exiting: true } : t))
      })
      clearFadeTimer(id)
      const fade = window.setTimeout(() => {
        setItems((prev) => prev.filter((t) => t.id !== id))
        fadeTimersRef.current.delete(id)
        clearAutoTimer(id)
      }, TOAST_FADE_MS)
      fadeTimersRef.current.set(id, fade)
    },
    [clearAutoTimer, clearFadeTimer],
  )

  const scheduleAutoDismiss = useCallback(
    (id: string, holdMs: number) => {
      clearAutoTimer(id)
      const timer = window.setTimeout(() => dismiss(id), holdMs)
      timersRef.current.set(id, timer)
    },
    [clearAutoTimer, dismiss],
  )

  const push = useCallback(
    (kind: ToastKind, message: string, opts?: ToastOptions) => {
      const text = message.trim()
      if (!text) return
      const now = Date.now()
      const sticky = isStickyDefault(kind, opts)
      const key = opts?.key?.trim() || undefined
      const last = lastPushRef.current
      if (
        !key &&
        last &&
        last.kind === kind &&
        last.message === text &&
        now - last.at < DEDUP_MS
      ) {
        return
      }
      lastPushRef.current = { kind, message: text, at: now }

      const existing = key
        ? itemsRef.current.find((t) => t.key === key && !t.exiting)
        : undefined
      const id = existing?.id ?? nextId()

      if (existing) {
        clearFadeTimer(id)
        setItems((prev) =>
          prev.map((t) =>
            t.id === id ? { ...t, kind, message: text, sticky, exiting: false, key } : t,
          ),
        )
      } else {
        setItems((prev) =>
          [
            ...prev.filter((t) => !(key && t.key === key)),
            { id, kind, message: text, exiting: false, sticky, key },
          ].slice(-5),
        )
      }

      if (sticky) clearAutoTimer(id)
      else scheduleAutoDismiss(id, holdMsFor(kind, opts))
    },
    [clearAutoTimer, clearFadeTimer, scheduleAutoDismiss],
  )

  const dismissKey = useCallback(
    (key: string) => {
      const k = key.trim()
      if (!k) return
      const hit = itemsRef.current.find((t) => t.key === k && !t.exiting)
      if (hit) dismiss(hit.id)
    },
    [dismiss],
  )

  const api = useMemo<ToastApi>(
    () => ({
      push,
      info: (message, opts) => push('info', message, opts),
      success: (message, opts) => push('success', message, opts),
      warn: (message, opts) => push('warn', message, opts),
      error: (message, opts) => push('error', message, opts),
      dismissKey,
    }),
    [push, dismissKey],
  )

  useEffect(() => {
    globalApi = api
    return () => {
      globalApi = null
      for (const timer of timersRef.current.values()) window.clearTimeout(timer)
      for (const timer of fadeTimersRef.current.values()) window.clearTimeout(timer)
      timersRef.current.clear()
      fadeTimersRef.current.clear()
    }
  }, [api])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-viewport" aria-live="polite" aria-relevant="additions text">
        {items.map((item) => (
          <ToastItem key={item.id} item={item} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// Separate ToastItem component to avoid ref access during render
function ToastItem({ item, onDismiss }: { item: ToastItem; onDismiss: (id: string) => void }) {
  const { id, kind, message, exiting, sticky } = item

  return (
    <div
      key={id}
      className={`toast-item toast-item--${kind}${exiting ? ' exiting' : ''}${sticky ? ' is-sticky' : ''}`}
      role={kind === 'warn' || kind === 'error' ? 'alert' : 'status'}
    >
      <button
        type="button"
        className="toast-close"
        aria-label="Dismiss"
        onClick={() => onDismiss(id)}
      >
        ×
      </button>
      <span className="toast-message">{message}</span>
    </div>
  )
}