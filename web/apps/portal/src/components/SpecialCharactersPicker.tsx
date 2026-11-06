import { useState, useCallback, useEffect, useRef } from 'react';
import { Search, ChevronLeft, ChevronRight, X, Check, Sparkles } from 'lucide-react';
import { useI18n } from '../contexts/I18nContext';

export interface CustomCharSet {
  category: string;
  chars: string[];
}

export interface SpecialCharactersPickerProps {
  onInsert?: (char: string) => void;
  isOpen?: boolean;
  onClose?: () => void;
  customCategories?: CustomCharSet[];
}

const DEFAULT_CATEGORIES: { id: string; name: string; pages: string[][] }[] = [
  {
    id: 'math',
    name: 'Math',
    pages: [
      // Page 1: Basic & Algebra
      ['±', '×', '÷', '=', '≠', '≈', '≤', '≥', '<', '>', '√', '∛', '∜', '²', '³', 'ⁿ', '½', '⅓', '¼', '%', '‰', '∞', '∝', '∠', '°', '⊥', '∥', '∴', '∵', '∎'],
      // Page 2: Calculus, Sets & Logic
      ['∫', '∬', '∭', '∮', '∂', '∇', '∑', '∏', '∈', '∉', '⊂', '⊃', '⊆', '⊇', '∪', '∩', '∅', '∧', '∨', '¬', '⇒', '⇔', '∀', '∃', '∄', '≡', '≢', '⊄', '⊅', '⊕'],
    ],
  },
  {
    id: 'chemistry',
    name: 'Chemistry',
    pages: [
      // Page 1: Arrows & Equilibrium
      ['→', '⇄', '⇌', '⇋', '↑', '↓', '↔', '⇒', '⥯', '⥮', '⥰', '⥱', '⥲', '⥳', '⥴', '∆', '·', '•', '≡', '═', '─', '℃', '℉', 'K', 'Å', '⦵', '⦶', '⦷', '⦸', '⦹'],
      // Page 2: Charges, Bonds & Subscripts
      ['⁺', '⁻', '²⁺', '³⁺', '⁴⁺', '²⁻', '³⁻', '⁴⁻', '⁰', '₁', '₂', '₃', '₄', '₅', '₆', '₇', '₈', '₉', '₊', '₋', '₍', '₎', '₀', 'α', 'β', 'γ', 'δ', 'σ', 'π', 'λ'],
    ],
  },
  {
    id: 'physics',
    name: 'Physics',
    pages: [
      // Page 1: Constants & Quanta
      ['ħ', 'ℏ', 'λ', 'ν', 'Ω', 'μ', 'ρ', 'σ', 'τ', 'φ', 'ψ', 'ω', 'Δ', '∇', 'c', 'G', 'h', 'k', 'ε₀', 'μ₀', 'e', 'mₑ', 'mₚ', 'mₙ', 'Å', '℃', '℉', 'K', 'J', 'W'],
      // Page 2: Units & Symbols
      ['N', 'Pa', 'V', 'A', 'T', 'Hz', 'Bq', 'Gy', 'Sv', 'ℓ', 'Å', '∢', '∡', '⊾', '⊿', '⊕', '⊗', '⊙', '⊘', '⊥', '∥', '∠', '∡', '⌒', '⌢', '⌣', '⌀', '⌁', '⌂', '⌃'],
    ],
  },
  {
    id: 'greek',
    name: 'Greek',
    pages: [
      // Page 1: Lowercase
      ['α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω', 'ϑ', 'ϕ', 'ϖ', 'ϰ', 'ϱ', 'ς'],
      // Page 2: Uppercase
      ['Α', 'Β', 'Γ', 'Δ', 'Ε', 'Ζ', 'Η', 'Θ', 'Ι', 'Κ', 'Λ', 'Μ', 'Ν', 'Ξ', 'Ο', 'Π', 'Ρ', 'Σ', 'Τ', 'Υ', 'Φ', 'Χ', 'Ψ', 'Ω', 'ϒ', 'ϓ', 'ϔ', '∇', '∏', '∑'],
    ],
  },
  {
    id: 'foreign',
    name: 'Foreign',
    pages: [
      // Page 1: Accents
      ['á', 'é', 'í', 'ó', 'ú', 'à', 'è', 'ì', 'ò', 'ù', 'â', 'ê', 'î', 'ô', 'û', 'ä', 'ë', 'ï', 'ö', 'ü', 'ÿ', 'ç', 'ñ', 'ß', 'æ', 'œ', 'ø', 'å', 'þ', 'ð'],
      // Page 2: Uppercase
      ['Á', 'É', 'Í', 'Ó', 'Ú', 'À', 'È', 'Ì', 'Ò', 'Ù', 'Â', 'Ê', 'Î', 'Ô', 'Û', 'Ä', 'Ë', 'Ï', 'Ö', 'Ü', 'Ÿ', 'Ç', 'Ñ', 'Æ', 'Œ', 'Ø', 'Å', 'Þ', 'Ð', 'Ł'],
      // Page 3: Symbols & Quotes
      ['ł', 'ŋ', 'ħ', 'š', 'ž', 'ř', 'č', 'ć', 'ń', 'ś', 'ź', 'ż', '¿', '¡', '«', '»', '„', '“', '”', '‘', '’', '‹', '›', '—', '–', '·', '•', '§', '¶', '©'],
    ],
  },
];

export function SpecialCharactersPicker({
  onInsert,
  isOpen: controlledIsOpen,
  onClose: controlledOnClose,
  customCategories = [],
}: SpecialCharactersPickerProps) {
  const { t } = useI18n();

  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = controlledIsOpen !== undefined ? controlledIsOpen : internalOpen;
  const onClose = controlledOnClose || (() => setInternalOpen(false));

  const [activeCategoryIdx, setActiveCategoryIdx] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const [search, setSearch] = useState('');
  const [copiedChar, setCopiedChar] = useState<string | null>(null);

  // Track active input in the DOM for direct insertion
  const lastActiveElementRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const handleFocusIn = (e: FocusEvent) => {
      const target = e.target as HTMLElement;
      if (
        target &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') &&
        !target.closest('[data-char-picker]')
      ) {
        lastActiveElementRef.current = target as HTMLInputElement | HTMLTextAreaElement;
      }
    };
    document.addEventListener('focusin', handleFocusIn);
    return () => document.removeEventListener('focusin', handleFocusIn);
  }, []);

  // Merge custom categories from exam module
  const categories = [...DEFAULT_CATEGORIES];
  if (customCategories.length > 0) {
    customCategories.forEach((cc, idx) => {
      // Chunk into pages of 30 chars
      const pages: string[][] = [];
      for (let i = 0; i < cc.chars.length; i += 30) {
        pages.push(cc.chars.slice(i, i + 30));
      }
      categories.push({
        id: `custom_${idx}`,
        name: cc.category,
        pages: pages.length > 0 ? pages : [[]],
      });
    });
  }

  const currentCategory = categories[activeCategoryIdx] || categories[0];
  const totalPages = currentCategory.pages.length;

  // Keyboard navigation for page flip (ArrowLeft / ArrowRight)
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement && e.target.type === 'text') {
        // If typing in search bar, handle Enter to jump to category
        if (e.key === 'Enter') {
          e.preventDefault();
          const query = search.trim().toLowerCase();
          if (query) {
            const foundIdx = categories.findIndex((c) =>
              c.name.toLowerCase().startsWith(query) || c.id.toLowerCase().startsWith(query)
            );
            if (foundIdx !== -1) {
              setActiveCategoryIdx(foundIdx);
              setCurrentPage(0);
              setSearch('');
            }
          }
        }
        return;
      }

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setCurrentPage((prev) => (prev > 0 ? prev - 1 : totalPages - 1));
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setCurrentPage((prev) => (prev < totalPages - 1 ? prev + 1 : 0));
      } else if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, search, categories, totalPages, onClose]);

  const insertCharacter = useCallback(
    (char: string) => {
      // 1. Direct insertion into DOM cursor position
      const target = lastActiveElementRef.current;
      if (target && 'value' in target) {
        const start = target.selectionStart ?? target.value.length;
        const end = target.selectionEnd ?? target.value.length;
        const val = target.value;
        target.value = val.substring(0, start) + char + val.substring(end);
        target.selectionStart = target.selectionEnd = start + char.length;
        target.dispatchEvent(new Event('input', { bubbles: true }));
        target.dispatchEvent(new Event('change', { bubbles: true }));
        target.focus();
      }

      // 2. Call external callback if given
      onInsert?.(char);

      // Visual feedback
      setCopiedChar(char);
      setTimeout(() => setCopiedChar(null), 1200);
    },
    [onInsert]
  );

  const prevPage = () => {
    setCurrentPage((prev) => (prev > 0 ? prev - 1 : totalPages - 1));
  };

  const nextPage = () => {
    setCurrentPage((prev) => (prev < totalPages - 1 ? prev + 1 : 0));
  };

  const displayedChars = (() => {
    if (search.trim()) {
      const q = search.toLowerCase();
      // Search across all categories
      const all: string[] = [];
      categories.forEach((cat) => {
        cat.pages.forEach((p) => {
          p.forEach((c) => {
            if (c.toLowerCase().includes(q) && !all.includes(c)) {
              all.push(c);
            }
          });
        });
      });
      return all.slice(0, 30);
    }
    return currentCategory.pages[currentPage] || [];
  })();

  // Trigger button if uncontrolled
  if (!isOpen) {
    return (
      <button
        onClick={() => setInternalOpen(true)}
        title={t('special_chars.title')}
        aria-label={t('special_chars.open')}
        style={{
          position: 'fixed',
          bottom: '1.5rem',
          right: '1.5rem',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          padding: '0.6rem 1rem',
          borderRadius: 'var(--radius-full)',
          border: '1px solid var(--border-color)',
          backgroundColor: 'var(--panel-bg)',
          color: 'var(--text-color)',
          boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
          cursor: 'pointer',
          fontWeight: 600,
          fontSize: '0.85rem',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.transform = 'translateY(0)'; }}
      >
        <Sparkles size={16} style={{ color: 'var(--primary-color)' }} />
        <span>{t('special_chars.button_label')}</span>
      </button>
    );
  }

  return (
    <div
      data-char-picker="true"
      style={{
        position: 'fixed',
        bottom: '1.5rem',
        right: '1.5rem',
        zIndex: 2500,
        width: '340px',
        maxHeight: '480px',
        backgroundColor: 'var(--panel-bg)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: '0 12px 40px rgba(0,0,0,0.3)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.65rem 0.9rem',
          backgroundColor: 'var(--sidebar-bg)',
          borderBottom: '1px solid var(--border-color)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Sparkles size={15} style={{ color: 'var(--primary-color)' }} />
          <span style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-color)' }}>
            {t('special_chars.title') || 'Symbols Picker'}
          </span>
        </div>
        <button
          onClick={onClose}
          aria-label="Close Character Picker"
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '0.2rem',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <X size={17} />
        </button>
      </div>

      {/* Search Bar with Page Navigation Icons */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.35rem',
          padding: '0.5rem 0.75rem',
          borderBottom: '1px solid var(--border-color)',
          backgroundColor: 'var(--bg-color)',
        }}
      >
        <div style={{ position: 'relative', flex: 1 }}>
          <Search
            size={14}
            style={{
              position: 'absolute',
              left: '0.6rem',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-muted)',
            }}
          />
          <input
            type="text"
            placeholder="Type 'math', 'chem' + Enter..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '0.4rem 0.5rem 0.4rem 1.8rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--panel-bg)',
              color: 'var(--text-color)',
              fontSize: '0.8rem',
            }}
          />
        </div>

        {/* Left & Right page flip icons next to search bar */}
        {!search.trim() && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.15rem' }}>
            <button
              onClick={prevPage}
              title="Previous Page (Left Arrow)"
              style={{
                background: 'none',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.3rem',
                cursor: 'pointer',
                display: 'flex',
                color: 'var(--text-color)',
              }}
            >
              <ChevronLeft size={14} />
            </button>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', padding: '0 0.25rem' }}>
              {currentPage + 1}/{totalPages}
            </span>
            <button
              onClick={nextPage}
              title="Next Page (Right Arrow)"
              style={{
                background: 'none',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.3rem',
                cursor: 'pointer',
                display: 'flex',
                color: 'var(--text-color)',
              }}
            >
              <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>

      {/* Category Pills */}
      {!search.trim() && (
        <div
          style={{
            display: 'flex',
            gap: '0.35rem',
            padding: '0.4rem 0.75rem',
            overflowX: 'auto',
            borderBottom: '1px solid var(--border-color)',
            backgroundColor: 'var(--sidebar-bg)',
          }}
        >
          {categories.map((cat, idx) => {
            const catLabel = cat.id.startsWith('custom-')
              ? cat.name
              : (t(`special_chars.${cat.id}`) || cat.name);
            return (
              <button
                key={cat.id}
                onClick={() => {
                  setActiveCategoryIdx(idx);
                  setCurrentPage(0);
                }}
                style={{
                  padding: '0.25rem 0.6rem',
                  borderRadius: 'var(--radius-full)',
                  border: `1px solid ${activeCategoryIdx === idx ? 'var(--primary-color)' : 'var(--border-color)'}`,
                  backgroundColor: activeCategoryIdx === idx ? 'var(--primary-color)' : 'transparent',
                  color: activeCategoryIdx === idx ? '#fff' : 'var(--text-color)',
                  fontSize: '0.75rem',
                  fontWeight: activeCategoryIdx === idx ? 600 : 400,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {catLabel}
              </button>
            );
          })}
        </div>
      )}

      {/* Character Grid */}
      <div
        style={{
          flex: 1,
          padding: '0.75rem',
          overflowY: 'auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(6, 1fr)',
          gap: '0.4rem',
        }}
      >
        {displayedChars.length === 0 ? (
          <div
            style={{
              gridColumn: '1 / -1',
              textAlign: 'center',
              padding: '1.5rem',
              color: 'var(--text-muted)',
              fontSize: '0.8rem',
            }}
          >
            {t('special_chars.empty') || 'No characters found'}
          </div>
        ) : (
          displayedChars.map((char, i) => {
            const isJustCopied = copiedChar === char;
            return (
              <button
                key={`${char}_${i}`}
                onClick={() => insertCharacter(char)}
                title={`Insert ${char}`}
                style={{
                  height: '42px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-color)',
                  backgroundColor: isJustCopied ? 'var(--success-color)' : 'var(--bg-color)',
                  color: isJustCopied ? '#fff' : 'var(--text-color)',
                  fontSize: '1.25rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  transition: 'background-color 0.1s',
                  lineHeight: 1,
                }}
              >
                {isJustCopied ? <Check size={16} /> : char}
              </button>
            );
          })
        )}
      </div>

      {/* Subtle Hint Footer */}
      <div
        style={{
          padding: '0.4rem 0.75rem',
          backgroundColor: 'var(--sidebar-bg)',
          borderTop: '1px solid var(--border-color)',
          fontSize: '0.7rem',
          color: 'var(--text-muted)',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <span>Click inserts at cursor position</span>
        <span>← / → flip pages</span>
      </div>
    </div>
  );
}
