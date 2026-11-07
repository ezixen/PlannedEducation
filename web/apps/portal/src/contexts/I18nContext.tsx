import { createContext, useContext, useState, useEffect, useCallback, useMemo, type ReactNode } from 'react';

import enMessages from '../locales/en/messages.json';
import { getKeyNumber } from '../locales/keyNumbers';

export type Locale = 'en' | 'ar' | 'bg' | 'cn' | 'cs' | 'da' | 'de' | 'el' | 'es' | 'et' | 'fi' | 'fr' | 'ga' | 'he' | 'hr' | 'hu' | 'id' | 'it' | 'ja' | 'ko' | 'lt' | 'lv' | 'mt' | 'nl' | 'no' | 'pl' | 'pt' | 'pt-BR' | 'ro' | 'ru' | 'sk' | 'sl' | 'sv' | 'th' | 'tr' | 'uk' | 'vi';

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
const AVAILABLE_LOCALES: Locale[] = ['en', 'ar', 'bg', 'cn', 'cs', 'da', 'de', 'el', 'es', 'et', 'fi', 'fr', 'ga', 'he', 'hr', 'hu', 'id', 'it', 'ja', 'ko', 'lt', 'lv', 'mt', 'nl', 'no', 'pl', 'pt', 'pt-BR', 'ro', 'ru', 'sk', 'sl', 'sv', 'th', 'tr', 'uk', 'vi'];

export const LOCALE_NAMES: Record<Locale, string> = {
  en: 'EN - UK/US English',
  ar: 'AR - Arabic (العربية)',
  bg: 'BG - Bulgarian',
  cn: 'CN - Chinese (中文)',
  cs: 'CS - Czech (Čeština)',
  da: 'DA - Danish',
  de: 'DE - German (Deutsch)',
  el: 'EL - Greek (Ελληνικά)',
  es: 'ES - Spanish (Español)',
  et: 'ET - Estonian',
  fi: 'FI - Finnish (Suomi)',
  fr: 'FR - French (Français)',
  ga: 'GA - Irish (Gaeilge)',
  he: 'HE - Hebrew (עברית)',
  hr: 'HR - Croatian',
  hu: 'HU - Hungarian (Magyar)',
  id: 'ID - Indonesian',
  it: 'IT - Italian (Italiano)',
  ja: 'JA - Japanese (日本語)',
  ko: 'KO - Korean (한국어)',
  lt: 'LT - Lithuanian',
  lv: 'LV - Latvian',
  mt: 'MT - Maltese',
  nl: 'NL - Dutch (Nederlands)',
  no: 'NO - Norwegian',
  pl: 'PL - Polish (Polski)',
  pt: 'PT - Portuguese',
  'pt-BR': 'PT-BR - Brazilian',
  ro: 'RO - Romanian',
  ru: 'RU - Russian (Русский)',
  sk: 'SK - Slovak',
  sl: 'SL - Slovenian',
  sv: 'SV - Swedish',
  th: 'TH - Thai (ไทย)',
  tr: 'TR - Turkish',
  uk: 'UK - Ukrainian',
  vi: 'VI - Vietnamese',
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
    const keyNum = getKeyNumber(key);
    const prefix = showNumbers ? (keyNum !== undefined ? `[#${keyNum}] ` : `[${key}] `) : '';

    if (!entry) {
      return showNumbers ? `${prefix}${key}` : key;
    }
    let text = typeof entry === 'string' ? entry : (entry[locale] || entry.en || key);
    if (params) {
      Object.entries(params).forEach(([paramKey, value]) => {
        text = text.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), value);
      });
    }
    return `${prefix}${text}`;
  }, [messages, locale, showNumbers]);

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