import { createContext, useContext, useState, useEffect, useCallback, useMemo, type ReactNode } from 'react';

import enMessages from '../locales/en/messages.json';

export type Locale = 'en' | 'hu' | 'es' | 'de' | 'fr' | 'ja' | 'zh' | 'pt' | 'uk' | 'it' | 'pl' | 'nl' | 'sv' | 'no' | 'da' | 'fi' | 'pt-BR';

export interface TranslationEntry {
  en: string;
  context?: string;
  [key: string]: string | undefined;
}

export interface LocaleMessages {
  [key: string]: TranslationEntry | string;
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
const AVAILABLE_LOCALES: Locale[] = ['en', 'hu', 'es', 'de', 'fr', 'ja', 'zh', 'pt', 'uk', 'it', 'pl', 'nl', 'sv', 'no', 'da', 'fi', 'pt-BR'];

export const LOCALE_NAMES: Record<Locale, string> = {
  en: 'EN - United Kingdom / United States (English)',
  hu: 'HU - Hungary (Magyar)',
  es: 'ES - Spain (Español)',
  de: 'DE - Germany (Deutsch)',
  fr: 'FR - France (Français)',
  ja: 'JA - Japan (日本語)',
  zh: 'ZH - China (中文)',
  pt: 'PT - Portugal (Português)',
  uk: 'UK - Ukraine (Українська)',
  it: 'IT - Italy (Italiano)',
  pl: 'PL - Poland (Polski)',
  nl: 'NL - Netherlands (Nederlands)',
  sv: 'SV - Sweden (Svenska)',
  no: 'NO - Norway (Norsk)',
  da: 'DA - Denmark (Dansk)',
  fi: 'FI - Finland (Suomi)',
  'pt-BR': 'PT-BR - Brazil (Português do Brasil)',
};

const localeModules = import.meta.glob<LocaleMessages>(['../locales/*/messages.json', '!../locales/en/messages.json'], { import: 'default' });

const messagesCache: Partial<Record<Locale, LocaleMessages>> = {
  en: enMessages as LocaleMessages,
};
const contextCache: Record<string, string> = {};

async function loadMessages(locale: Locale): Promise<LocaleMessages> {
  if (messagesCache[locale]) {
    return messagesCache[locale]!;
  }
  const modulePath = `../locales/${locale}/messages.json`;
  const loader = localeModules[modulePath];
  if (loader) {
    try {
      const data = await loader();
      messagesCache[locale] = data;
      return data;
    } catch (e) {
      console.warn(`Failed to load bundled messages for ${locale}:`, e);
    }
  }
  return enMessages as LocaleMessages;
}

export function I18nProvider({ children, initialLocale = DEFAULT_LOCALE }: { children: ReactNode; initialLocale?: Locale }) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);
  const [showNumbers, setShowNumbers] = useState(false);
  const [messages, setMessages] = useState<LocaleMessages>(enMessages as LocaleMessages);
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
    const entry = messages[key] ?? (enMessages as LocaleMessages)[key];
    if (!entry) {
      return key;
    }
    let text = typeof entry === 'string' ? entry : (entry[locale] || entry.en || key);
    if (params) {
      Object.entries(params).forEach(([paramKey, value]) => {
        text = text.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), value);
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