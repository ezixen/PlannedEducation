import { createContext, useContext, useState, useEffect, useCallback, useMemo, ReactNode } from 'react';

export type Locale = 'en' | 'hu' | 'es' | 'de' | 'fr' | 'ja' | 'zh';

export interface TranslationEntry {
  en: string;
  context?: string;
  [key: string]: string | undefined;
}

export interface LocaleMessages {
  [key: string]: TranslationEntry;
}

export interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  showNumbers: boolean;
  setShowNumbers: (show: boolean) => void;
  t: (key: string, params?: Record<string, string>) => string;
  getContext: (key: string) => string | undefined;
  jumpToElement: (key: string) => void;
  availableLocales: Locale[];
}

const I18nContext = createContext<I18nContextType | null>(null);

const DEFAULT_LOCALE: Locale = 'en';
const AVAILABLE_LOCALES: Locale[] = ['en', 'hu', 'es', 'de', 'fr', 'ja', 'zh'];

const LOCALE_NAMES: Record<Locale, string> = {
  en: 'English',
  hu: 'Magyar',
  es: 'Español',
  de: 'Deutsch',
  fr: 'Français',
  ja: '日本語',
  zh: '中文',
};

let messagesCache: Record<Locale, LocaleMessages> = {} as Record<Locale, LocaleMessages>;
let contextCache: Record<string, string> = {};

async function loadMessages(locale: Locale): Promise<LocaleMessages> {
  if (messagesCache[locale]) {
    return messagesCache[locale];
  }
  try {
    const response = await fetch(`/locales/${locale}/messages.json`);
    if (response.ok) {
      const data = await response.json();
      messagesCache[locale] = data;
      return data;
    }
  } catch (e) {
    console.warn(`Failed to load messages for ${locale}:`, e);
  }
  return {};
}

async function loadContext(): Promise<void> {
  if (Object.keys(contextCache).length > 0) return;
  try {
    const response = await fetch('/locales/en/CONTEXT.md');
    if (response.ok) {
      const text = await response.text();
      parseContextMarkdown(text);
    }
  } catch (e) {
    console.warn('Failed to load context:', e);
  }
}

function parseContextMarkdown(markdown: string): void {
  const lines = markdown.split('\n');
  let currentKey = '';
  let currentContext = '';
  
  for (const line of lines) {
    const keyMatch = line.match(/^###\s+(\S+)/);
    if (keyMatch) {
      if (currentKey && currentContext) {
        contextCache[currentKey] = currentContext.trim();
      }
      currentKey = keyMatch[1];
      currentContext = '';
    } else if (currentKey) {
      currentContext += line + '\n';
    }
  }
  if (currentKey && currentContext) {
    contextCache[currentKey] = currentContext.trim();
  }
}

export function I18nProvider({ children, initialLocale = DEFAULT_LOCALE }: { children: ReactNode; initialLocale?: Locale }) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);
  const [showNumbers, setShowNumbers] = useState(false);
  const [messages, setMessages] = useState<LocaleMessages>({});
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const savedLocale = localStorage.getItem('locale') as Locale | null;
    const savedShowNumbers = localStorage.getItem('showNumbers') === 'true';
    if (savedLocale && AVAILABLE_LOCALES.includes(savedLocale)) {
      setLocaleState(savedLocale);
    }
    setShowNumbers(savedShowNumbers);
    loadMessages(savedLocale || initialLocale).then(setMessages);
    loadContext();
  }, [initialLocale]);

  useEffect(() => {
    if (!mounted) return;
    localStorage.setItem('locale', locale);
    loadMessages(locale).then(setMessages);
  }, [locale, mounted]);

  useEffect(() => {
    if (!mounted) return;
    localStorage.setItem('showNumbers', showNumbers.toString());
  }, [showNumbers, mounted]);

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
  }, []);

  const setShowNumbersState = useCallback((show: boolean) => {
    setShowNumbers(show);
  }, []);

  const t = useCallback((key: string, params?: Record<string, string>): string => {
    const entry = messages[key];
    if (!entry) {
      console.warn(`Missing translation key: ${key}`);
      return key;
    }
    let text = entry[locale] || entry.en || key;
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        text = text.replace(new RegExp(`\\{${key}\\}`, 'g'), value);
      });
    }
    return text;
  }, [messages, locale]);

  const getContext = useCallback((key: string): string | undefined => {
    return contextCache[key];
  }, []);

  const jumpToElement = useCallback((key: string) => {
    const element = document.querySelector(`[data-i18n-key="${key}"]`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
      element.classList.add('i18n-highlight');
      setTimeout(() => element.classList.remove('i18n-highlight'), 3000);
    }
  }, []);

  const value = useMemo(() => ({
    locale,
    setLocale,
    showNumbers,
    setShowNumbers: setShowNumbersState,
    t,
    getContext,
    jumpToElement,
    availableLocales: AVAILABLE_LOCALES,
  }), [locale, showNumbers, messages]);

  if (!mounted) {
    return <>{children}</>;
  }

  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextType {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

export function useTranslation() {
  const { t, locale, setLocale, showNumbers, setShowNumbers, jumpToElement, availableLocales } = useI18n();
  return { t, locale, setLocale, showNumbers, setShowNumbers, jumpToElement, availableLocales, localeNames: LOCALE_NAMES };
}

export function getLocaleName(locale: Locale): string {
  return LOCALE_NAMES[locale] || locale;
}