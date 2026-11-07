import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { Globe, ChevronDown } from 'lucide-react';
import { useI18n, LOCALE_NAMES, type Locale } from '../contexts/I18nContext';

interface LanguageSelectorProps {
  /** Compact pill (header) vs full-width block (auth forms / menu). */
  variant?: 'pill' | 'block';
  className?: string;
}

/** Reusable locale switcher — fixed menu clamped inside the viewport in windowed mode. */
export function LanguageSelector({ variant = 'pill', className }: LanguageSelectorProps) {
  const { locale, setLocale, availableLocales, t } = useI18n();
  const [open, setOpen] = useState(false);
  const [menuPos, setMenuPos] = useState<{ top: number; left: number; width: number; maxHeight: number } | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();

  useLayoutEffect(() => {
    if (!open || !rootRef.current) {
      setMenuPos(null);
      return;
    }
    const place = () => {
      const rect = rootRef.current!.getBoundingClientRect();
      const gutter = 8;
      const width = Math.min(240, Math.max(160, window.innerWidth - gutter * 2));
      let left = rect.right - width;
      if (left < gutter) left = gutter;
      if (left + width > window.innerWidth - gutter) {
        left = Math.max(gutter, window.innerWidth - width - gutter);
      }
      const top = Math.min(rect.bottom + 6, window.innerHeight - gutter - 80);
      const maxHeight = Math.max(120, Math.min(288, window.innerHeight - top - gutter));
      setMenuPos({ top, left, width, maxHeight });
    };
    place();
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    return () => {
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', place, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const pick = (loc: Locale) => {
    setLocale(loc);
    setOpen(false);
  };

  if (variant === 'block') {
    return (
      <div className={className} style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', textAlign: 'left' }}>
        <label
          htmlFor="pe-lang-select-block"
          style={{
            fontSize: '0.75rem',
            fontWeight: 600,
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
          }}
        >
          <Globe size={14} /> {t('settings.section_language')}
        </label>
        <select
          id="pe-lang-select-block"
          value={locale}
          onChange={(e) => setLocale(e.target.value as Locale)}
          aria-label={t('layout.select_language')}
          style={{
            width: '100%',
            maxWidth: '100%',
            padding: '0.5rem 0.65rem',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-color)',
            color: 'var(--text-color)',
            fontSize: '0.9rem',
            cursor: 'pointer',
          }}
        >
          {availableLocales.map((loc) => (
            <option key={loc} value={loc}>
              {LOCALE_NAMES[loc] || loc.toUpperCase()}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div
      ref={rootRef}
      className={`header-lang-pill header-lang-dropdown${className ? ` ${className}` : ''}`}
    >
      <Globe size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} aria-hidden />
      <button
        type="button"
        className="header-lang-trigger"
        aria-label={t('layout.select_language')}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="header-lang-trigger-text" title={LOCALE_NAMES[locale] || locale.toUpperCase()}>
          {locale.toUpperCase()}
        </span>
        <ChevronDown size={14} aria-hidden />
      </button>
      {open && menuPos && (
        <ul
          id={listId}
          role="listbox"
          aria-label={t('layout.select_language')}
          className="header-lang-menu pe-modal-surface"
          data-pe-modal="true"
          style={{
            position: 'fixed',
            top: menuPos.top,
            left: menuPos.left,
            right: 'auto',
            width: menuPos.width,
            maxWidth: menuPos.width,
            maxHeight: menuPos.maxHeight,
            zIndex: 4000,
          }}
        >
          {availableLocales.map((loc) => (
            <li key={loc} role="option" aria-selected={loc === locale}>
              <button
                type="button"
                className={`header-lang-option${loc === locale ? ' active' : ''}`}
                onClick={() => pick(loc)}
              >
                {LOCALE_NAMES[loc] || loc.toUpperCase()}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
