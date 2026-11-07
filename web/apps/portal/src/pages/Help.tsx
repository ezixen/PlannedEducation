import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useI18n } from '../contexts/I18nContext';
import { LanguageSelector } from '../components/LanguageSelector';
import { FAQChatbot } from '../components/FAQChatbot';

/**
 * Dedicated Help page — open from the menu in a new tab so the current
 * screen stays available while reading.
 */
export function Help() {
  const { t } = useI18n();

  return (
    <div className="help-page">
      <header className="help-page-header">
        <div className="help-page-header-row">
          <Link to="/" className="help-page-back">
            <ArrowLeft size={18} aria-hidden />
            <span>{t('help.back_home')}</span>
          </Link>
          <h1 className="help-page-title">{t('help.page_title')}</h1>
          <LanguageSelector variant="pill" />
        </div>
        <p className="help-page-subtitle">{t('help.page_subtitle')}</p>
      </header>
      <main className="help-page-main">
        <FAQChatbot variant="page" isOpen showFloatingButton={false} />
      </main>
    </div>
  );
}
