import { useI18n, LOCALE_NAMES } from '../contexts/I18nContext';
import './I18nSettings.css';

export function I18nSettings() {
  const { locale, setLocale, showNumbers, setShowNumbers, availableLocales, t } = useI18n();

  return (
    <div className="i18n-settings-panel">
      <h3 className="i18n-settings-title">{t('settings.i18n.title') || 'Language & Translation'}</h3>
      <p className="i18n-settings-desc">{t('settings.i18n.desc') || 'Configure language and translation display options'}</p>

      {/* Language Selector */}
      <div className="i18n-settings-section">
        <label className="i18n-settings-label" htmlFor="locale-select">
          {t('settings.i18n.language') || 'Language'}
        </label>
        <select
          id="locale-select"
          className="i18n-locale-select"
          value={locale}
          onChange={(e) => setLocale(e.target.value as any)}
        >
          {availableLocales.map((loc) => (
            <option key={loc} value={loc}>
              {LOCALE_NAMES[loc] || loc}
            </option>
          ))}
        </select>
        <p className="i18n-settings-hint">
          {t('settings.i18n.language_hint') || 'Changes take effect immediately. Translations are community-contributed.'}
        </p>
      </div>

      {/* Number Display Toggle */}
      <div className="i18n-settings-section">
        <label className="i18n-toggle-label">
          <input
            type="checkbox"
            id="show-numbers-toggle"
            checked={showNumbers}
            onChange={(e) => setShowNumbers(e.target.checked)}
          />
          <span className="i18n-toggle-text">
            <strong>{t('settings.i18n.show_numbers') || 'Show Translation Numbers'}</strong>
            <span className="i18n-toggle-desc">
              {t('settings.i18n.show_numbers_desc') || 'Display numbered badges on all translatable elements. Hover for context and jump-to functionality.'}
            </span>
          </span>
        </label>
      </div>

      {/* Help Section */}
      <details className="i18n-help-details">
        <summary className="i18n-help-summary">
          {t('settings.i18n.help_title') || 'How Translation Numbers Work'}
        </summary>
        <div className="i18n-help-content">
          <ul>
            <li>{t('settings.i18n.help_1') || 'Each translatable element has a unique number (e.g., <code>login.3</code> = "Email" field on login page)'}</li>
            <li>{t('settings.i18n.help_2') || 'Enable "Show Translation Numbers" to see badges on all translatable elements'}</li>
            <li>{t('settings.i18n.help_3') || 'Hover any numbered element to see its key, English text, and context'}</li>
            <li>{t('settings.i18n.help_4') || 'Click "Jump" in tooltip or press Enter on focused element to center it on screen'}</li>
            <li>{t('settings.i18n.help_5') || 'FAQ chatbot shows translation keys - click to jump directly to that element'}</li>
            <li>{t('settings.i18n.help_6') || 'Translators: use the key (e.g., <code>login.3</code>) to find and translate the correct text in locale files'}</li>
          </ul>
        </div>
      </details>

      {/* Translator Guide Link */}
      <div className="i18n-translator-guide">
        <a
          href="/docs/dev/I18N_CONTEXT.md"
          target="_blank"
          rel="noopener noreferrer"
          className="i18n-guide-link"
        >
          📖 {t('settings.i18n.translator_guide') || 'Open Translator Context Guide (CONTEXT.md)'}
        </a>
        <p className="i18n-guide-desc">
          {t('settings.i18n.translator_guide_desc') || 'Detailed context for every translation key: location, purpose, constraints, and screenshots.'}
        </p>
      </div>

      {/* Contribute Translation */}
      <div className="i18n-contribute">
        <h4>{t('settings.i18n.contribute_title') || 'Help Translate PlannedEducation'}</h4>
        <p>{t('settings.i18n.contribute_desc') || 'Missing your language? Found a mistake? Contributions welcome!'}</p>
        <div className="i18n-contribute-actions">
          <a
            href="https://github.com/ezixen/PlannedEducation/tree/main/web/apps/portal/src/locales"
            target="_blank"
            rel="noopener noreferrer"
            className="i18n-btn i18n-btn-primary"
          >
            View Locale Files on GitHub
          </a>
          <a
            href="https://github.com/ezixen/PlannedEducation/issues/new?template=translation.yml"
            target="_blank"
            rel="noopener noreferrer"
            className="i18n-btn i18n-btn-secondary"
          >
            Request New Language
          </a>
        </div>
      </div>
    </div>
  );
}