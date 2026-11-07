import { useId, useState } from 'react';
import { Info } from 'lucide-react';
import { useI18n } from '../contexts/I18nContext';

interface InfoTipProps {
  /** i18n key under info.* (or any key) for the tip body */
  tipKey: string;
  /** Optional accessible label override */
  label?: string;
  className?: string;
}

/**
 * Compact “i” tip: hover/focus popover clamped to the viewport.
 * Bubble text wraps; surface is opaque (data-pe-modal).
 */
export function InfoTip({ tipKey, label, className }: InfoTipProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const tipId = useId();
  const text = t(tipKey);
  const aria = label || t('info.tip_aria');

  return (
    <span className={`pe-info-tip${className ? ` ${className}` : ''}`}>
      <button
        type="button"
        className="pe-info-tip-btn"
        aria-label={aria}
        aria-describedby={open ? tipId : undefined}
        aria-expanded={open}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={(e) => {
          e.preventDefault();
          setOpen((v) => !v);
        }}
      >
        <Info size={14} aria-hidden />
      </button>
      {open && (
        <span
          id={tipId}
          role="tooltip"
          className="pe-info-tip-bubble pe-modal-surface"
          data-pe-modal="true"
        >
          {text}
        </span>
      )}
    </span>
  );
}
