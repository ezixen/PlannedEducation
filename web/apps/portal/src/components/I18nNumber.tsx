import { useI18n } from '../contexts/I18nContext';
import { useState, useEffect, useRef } from 'react';

interface I18nNumberProps {
  key: string;
  children: React.ReactNode;
  className?: string;
  tag?: keyof JSX.IntrinsicElements;
}

export function I18nNumber({ key, children, className = '', tag = 'span' }: I18nNumberProps) {
  const { showNumbers, t, getContext, jumpToElement } = useI18n();
  const [showTooltip, setShowTooltip] = useState(false);
  const [context, setContext] = useState<string | undefined>(undefined);
  const containerRef = useRef<HTMLSpanElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const contextText = getContext(key);
    setContext(contextText);
  }, [key, getContext]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      jumpToElement(key);
    }
  };

  if (!showNumbers) {
    return <>{children}</>;
  }

  const Tag = tag;
  const number = key.split('.').pop() || key;

  return (
    <span className="i18n-number-container" ref={containerRef}>
      <Tag
        className={`i18n-numbered-element ${className}`}
        data-i18n-key={key}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="button"
        aria-label={`Translation key: ${key}`}
      >
        {children}
        <span className="i18n-number-badge" aria-hidden="true">
          {number}
        </span>
      </Tag>

      {showTooltip && (
        <div
          ref={tooltipRef}
          className="i18n-tooltip"
          role="tooltip"
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          <div className="i18n-tooltip-header">
            <strong>Key:</strong> {key}
            <button
              className="i18n-jump-btn"
              onClick={(e) => {
                e.stopPropagation();
                jumpToElement(key);
              }}
              aria-label="Jump to this element"
            >
              ↻ Jump
            </button>
          </div>
          <div className="i18n-tooltip-text">
            {t(key)}
          </div>
          {context && (
            <div className="i18n-tooltip-context">
              <strong>Context:</strong>
              <pre>{context}</pre>
            </div>
          )}
        </div>
      )}
    </span>
  );
}

export function I18nText({ key, params, className = '' }: { key: string; params?: Record<string, string>; className?: string }) {
  const { t, showNumbers, getContext, jumpToElement } = useI18n();
  const [showTooltip, setShowTooltip] = useState(false);
  const [context, setContext] = useState<string | undefined>(undefined);
  const containerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const contextText = getContext(key);
    setContext(contextText);
  }, [key, getContext]);

  const text = t(key, params);

  if (!showNumbers) {
    return <span className={className}>{text}</span>;
  }

  const number = key.split('.').pop() || key;

  return (
    <span className="i18n-number-container" ref={containerRef}>
      <span
        className={`i18n-numbered-element ${className}`}
        data-i18n-key={key}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={() => jumpToElement(key)}
        tabIndex={0}
        role="button"
        aria-label={`Translation key: ${key}`}
      >
        {text}
        <span className="i18n-number-badge" aria-hidden="true">
          {number}
        </span>
      </span>

      {showTooltip && (
        <div className="i18n-tooltip" role="tooltip">
          <div className="i18n-tooltip-header">
            <strong>Key:</strong> {key}
            <button
              className="i18n-jump-btn"
              onClick={(e) => {
                e.stopPropagation();
                jumpToElement(key);
              }}
              aria-label="Jump to this element"
            >
              ↻ Jump
            </button>
          </div>
          <div className="i18n-tooltip-text">
            {text}
          </div>
          {context && (
            <div className="i18n-tooltip-context">
              <strong>Context:</strong>
              <pre>{context}</pre>
            </div>
          )}
        </div>
      )}
    </span>
  );
}

export function I18nNumberDisplay({ key, className = '' }: { key: string; className?: string }) {
  const { showNumbers } = useI18n();
  
  if (!showNumbers) return null;
  
  const number = key.split('.').pop() || key;
  
  return (
    <span className={`i18n-number-display ${className}`} aria-hidden="true">
      {number}
    </span>
  );
}