import { useState, useCallback } from 'react';
import { Search, Check } from 'lucide-react';
import { useI18n } from '../contexts/I18nContext';

interface SpecialCharactersPickerProps {
  onInsert: (char: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

const MATH_SYMBOLS = [
  '∑', '∆', '∞', 'π', '√', '³', '²', '≤', '≥', '≠', '±', '×', '÷', '≈', '∝',
  '∫', '∂', '∇', '∈', '∉', '⊂', '⊃', '∪', '∩', '∅', '∠', '°', '⊥', '∥', '∴',
];

const GREEK_LETTERS = [
  'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο',
  'π', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω',
  'Α', 'Β', 'Γ', 'Δ', 'Ε', 'Ζ', 'Η', 'Θ', 'Ι', 'Κ', 'Λ', 'Μ', 'Ν', 'Ξ', 'Ο',
  'Π', 'Ρ', 'Σ', 'Τ', 'Υ', 'Φ', 'Χ', 'Ψ', 'Ω',
];

const FOREIGN_CHARS = [
  'ñ', '¿', '¡', 'ß', 'æ', 'œ', 'ø', 'å', 'þ', 'ð', 'ł', 'ŋ', 'ħ',
  '¡', '¿', '«', '»', '„', '‚', '«', '»', '‹', '›',
];

const ACCENTED_CHARS = [
  'á', 'é', 'í', 'ó', 'ú', 'à', 'è', 'ì', 'ò', 'ù', 'â', 'ê', 'î', 'ô', 'û',
  'ä', 'ë', 'ï', 'ö', 'ü', 'ÿ', 'ã', 'õ', 'ñ', 'ç', 'š', 'ž', 'ř', 'č',
  'Á', 'É', 'Í', 'Ó', 'Ú', 'À', 'È', 'Ì', 'Ò', 'Ù', 'Â', 'Ê', 'Î', 'Ô', 'Û',
  'Ä', 'Ë', 'Ï', 'Ö', 'Ü', 'Ÿ', 'Ã', 'Õ', 'Ñ', 'Ç', 'Š', 'Ž', 'Ř', 'Č',
];

interface CharCategory {
  id: string;
  label: string;
  chars: string[];
}

const CATEGORIES: CharCategory[] = [
  { id: 'all', label: 'all', chars: [] },
  { id: 'math', label: 'math', chars: MATH_SYMBOLS },
  { id: 'greek', label: 'greek', chars: GREEK_LETTERS },
  { id: 'foreign', label: 'foreign', chars: FOREIGN_CHARS },
  { id: 'accents', label: 'accents', chars: ACCENTED_CHARS },
];

export function SpecialCharactersPicker({
  onInsert,
  isOpen,
  onClose,
}: SpecialCharactersPickerProps) {
  const { t } = useI18n();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [copied, setCopied] = useState<string | null>(null);

  const filteredChars = useCallback(() => {
    let chars: string[] = [];
    if (category === 'all') {
      chars = [...MATH_SYMBOLS, ...GREEK_LETTERS, ...FOREIGN_CHARS, ...ACCENTED_CHARS];
    } else {
      const cat = CATEGORIES.find((c) => c.id === category);
      chars = cat ? [...cat.chars] : [];
    }
    if (search.trim()) {
      const s = search.toLowerCase();
      chars = chars.filter((c) => c.toLowerCase().includes(s));
    }
    return chars;
  }, [search, category]);

  const handleInsert = useCallback((char: string) => {
    onInsert(char);
    setCopied(char);
    setTimeout(() => setCopied(null), 1500);
  }, [onInsert]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 2000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.4)',
          zIndex: -1,
        }}
        onClick={onClose}
      />

      <div
        style={{
          backgroundColor: 'var(--panel-bg)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          padding: '1.5rem',
          width: '420px',
          maxHeight: '600px',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text-color)' }}>
            {t('special_chars.title')}
          </h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '0.25rem',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <span>×</span>
          </button>
        </div>

        <div style={{ position: 'relative' }}>
          <Search
            size={16}
            style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
          />
          <input
            type="text"
            placeholder={t('special_chars.search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '0.6rem 0.75rem 0.6rem 2.25rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-color)',
              color: 'var(--text-color)',
              fontSize: '0.9rem',
            }}
          />
        </div>

        <div
          style={{
            display: 'flex',
            gap: '0.5rem',
            overflowX: 'auto',
            paddingBottom: '0.5rem',
          }}
        >
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setCategory(cat.id)}
              style={{
                padding: '0.4rem 0.8rem',
                borderRadius: 'var(--radius-full)',
                border: `1px solid ${category === cat.id ? 'var(--primary-color)' : 'var(--border-color)'}`,
                backgroundColor: category === cat.id ? 'var(--primary-color)' : 'transparent',
                color: category === cat.id ? '#fff' : 'var(--text-color)',
                fontSize: '0.85rem',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              {t(`special_chars.${cat.label}` as any)}
            </button>
          ))}
        </div>

        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(8, 1fr)',
            gap: '0.5rem',
          }}
        >
          {filteredChars().length === 0 ? (
            <div
              style={{
                gridColumn: '1 / -1',
                textAlign: 'center',
                padding: '2rem',
                color: 'var(--text-muted)',
                fontSize: '0.9rem',
              }}
            >
              {t('special_chars.empty')}
            </div>
          ) : (
            filteredChars().map((char) => {
              const isCopied = copied === char;
              return (
                <button
                  key={char}
                  onClick={() => handleInsert(char)}
                  title={t('special_chars.insert')}
                  style={{
                    padding: '0.75rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: isCopied ? 'var(--success-color)' : 'var(--bg-color)',
                    color: isCopied ? '#fff' : 'var(--text-color)',
                    fontSize: '1.5rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    lineHeight: 1,
                  }}
                >
                  {char}
                  {isCopied && (
                    <Check size={14} style={{ color: '#fff', marginLeft: '0.25rem' }} />
                  )}
                </button>
              );
            })
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
          <button
            onClick={onClose}
            style={{
              padding: '0.6rem 1rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              backgroundColor: 'transparent',
              color: 'var(--text-color)',
              fontSize: '0.9rem',
              cursor: 'pointer',
            }}
          >
            {t('special_chars.insert')}
          </button>
        </div>
      </div>
    </div>
  );
}