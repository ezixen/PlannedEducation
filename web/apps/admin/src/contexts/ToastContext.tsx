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

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const dedupRef = useRef<Map<string, number>>(new Map())

  const push = useCallback((kind: ToastKind, message: string, opts?: ToastOptions) => {
    const text = message.trim()
    if (!text) return

    const now = Date.now()
    const dedupKey = `${kind}:${text}`
    const last = dedupRef.current.get(dedupKey)
    if (last && now - last < DEDUP_MS) return
    dedupRef.current.set(dedupKey, now)

    const id = nextId()
    const sticky = isStickyDefault(kind, opts)

    setToasts(prev => [...prev, { id, kind, message: text, exiting: false, sticky, key: opts?.key }])

    const holdMs = holdMsFor(kind, opts)
    if (!sticky && holdMs > 0) {
      setTimeout(() => {
        setToasts(prev => prev.map(t => t.id === id ? { ...t, exiting: true } : t))
        setTimeout(() => {
          setToasts(prev => prev.filter(t => t.id !== id))
        }, TOAST_FADE_MS)
      }, holdMs)
    }
  }, [])

  const dismissKey = useCallback((key: string) => {
    setToasts(prev => prev.filter(t => t.key !== key))
  }, [])

  const api = useMemo<ToastApi>(() => ({
    push,
    info: (m, o) => push('info', m, o),
    success: (m, o) => push('success', m, o),
    warn: (m, o) => push('warn', m, o),
    error: (m, o) => push('error', m, o),
    dismissKey,
  }), [push, dismissKey])

  useEffect(() => {
    globalApi = api
    return () => { globalApi = null }
  }, [api])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div style={{ position: 'fixed', bottom: '1.5rem', right: '1.5rem', zIndex: 9999, display: 'flex', flexDirection: 'column', gap: '0.5rem', pointerEvents: 'none' }}>
        {toasts.map(t => (
          <div
            key={t.id}
            style={{
              pointerEvents: 'auto',
              padding: '0.875rem 1.25rem',
              borderRadius: 'var(--radius-lg)',
              backgroundColor: t.kind === 'error' ? '#fef2f2' : t.kind === 'warn' ? '#fffbeb' : t.kind === 'success' ? '#f0fdf4' : '#eff6ff',
              border: `1px solid ${t.kind === 'error' ? '#fecaca' : t.kind === 'warn' ? '#fde68a' : t.kind === 'success' ? '#bbf7d0' : '#bfdbfe'}`,
              color: t.kind === 'error' ? '#dc2626' : t.kind === 'warn' ? '#b45309' : t.kind === 'success' ? '#166534' : '#1e40af',
              boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.05)',
              minWidth: '280px',
              maxWidth: '420px',
              opacity: t.exiting ? 0 : 1,
              transform: t.exiting ? 'translateX(100%)' : 'translateX(0)',
              transition: 'opacity 0.3s ease, transform 0.3s ease',
              fontSize: '0.9rem',
              fontWeight: 500,
            }}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}