import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, Home, Settings, GraduationCap, LogOut, BookOpen, Users, BrainCircuit, Globe, ArrowLeft, Plus, Shield } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useI18n, LOCALE_NAMES } from '../contexts/I18nContext';
import { WatermarkOverlay } from './WatermarkOverlay';
import { FAQChatbot } from './FAQChatbot';
import { NotificationBell } from './NotificationBell';
import { apiClient } from '../api';

interface DeploymentConfig {
  school_name?: string;
  header_mode?: 'text' | 'image' | 'none';
  header_image_url?: string | null;
}

export function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const { locale, setLocale, availableLocales, t } = useI18n();
  const location = useLocation();
  const navigate = useNavigate();
  const [headerConfig, setHeaderConfig] = useState<DeploymentConfig>({});

  // Close menu on route changes
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  // Close menu on Escape key
  useEffect(() => {
    if (!menuOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [menuOpen]);

  // Load custom header branding
  useEffect(() => {
    let isMounted = true;
    const loadHeaderConfig = async () => {
      try {
        const res = await apiClient.get<DeploymentConfig>('/admin/config');
        if (isMounted) setHeaderConfig(res.data);
      } catch {
        // Fall back to defaults
      }
    };
    loadHeaderConfig();
    return () => {
      isMounted = false;
    };
  }, []);

  const getNavItems = () => {
    const baseItems = [
      { path: '/', label: t('nav.dashboard'), icon: <Home size={20} />, roles: ['student', 'teacher', 'parent', 'admin'] },
      { path: '/exam', label: t('nav.take_exam'), icon: <GraduationCap size={20} />, roles: ['student', 'teacher', 'parent', 'admin'] },
      { path: '/teacher-classes', label: t('nav.classes'), icon: <Users size={20} />, roles: ['teacher', 'admin'] },
      { path: '/teacher-exams', label: t('nav.exam_editor'), icon: <BookOpen size={20} />, roles: ['teacher', 'admin'] },
      { path: '/ai-grading', label: t('nav.ai_grading'), icon: <Plus size={20} />, roles: ['teacher', 'admin'] },
      { path: '/parent-dashboard', label: t('nav.parent_dashboard'), icon: <Users size={20} />, roles: ['parent', 'admin'] },
      { path: '/ai-integrations', label: t('nav.ai_integrations'), icon: <BrainCircuit size={20} />, roles: ['teacher', 'admin'] },
      { path: '/admin', label: t('nav.admin'), icon: <Shield size={20} />, roles: ['admin'] },
      { path: '/settings', label: t('nav.settings'), icon: <Settings size={20} />, roles: ['student', 'teacher', 'parent', 'admin'] },
    ];

    if (user?.is_admin) {
      return baseItems;
    }
    const userRole = user?.role;
    return baseItems.filter(item => !item.roles || !userRole || item.roles.includes(userRole));
  };

  const navItems = getNavItems();

  const handleBack = () => {
    const path = location.pathname;
    if (path === '/' || path === '/dashboard') {
      navigate('/');
    } else if (path.startsWith('/teacher-exams/')) {
      navigate('/teacher-exams');
    } else if (path.startsWith('/teacher-dashboard/')) {
      navigate('/teacher-exams');
    } else if (path.startsWith('/exam/')) {
      navigate('/exam');
    } else {
      navigate(-1);
    }
  };

  const isBackAvailable = location.pathname !== '/' && location.pathname !== '/dashboard';

  return (
    <div className="app-container">
      <WatermarkOverlay />

      {/* Floating Navigation Controls (Hamburger Menu & Back Button) */}
      <div className="floating-nav-controls">
        <button
          type="button"
          onClick={() => setMenuOpen((prev) => !prev)}
          className={`floating-nav-btn floating-hamburger-btn ${menuOpen ? 'active' : ''}`}
          aria-expanded={menuOpen}
          aria-label={t('layout.toggle_menu')}
          title={t('layout.toggle_menu')}
        >
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>

        {isBackAvailable && !menuOpen && (
          <button
            type="button"
            onClick={handleBack}
            className="floating-nav-btn floating-back-btn"
            aria-label={t('nav.back')}
            title={t('nav.back')}
          >
            <ArrowLeft size={18} />
          </button>
        )}
      </div>

      {/* Top Header - In Document Flow, Scrolls Away Naturally */}
      <header className="site-header">
        <div className="site-header-spacer" aria-hidden="true" />
        <div className="site-header-branding">
          {headerConfig.header_mode === 'image' && headerConfig.header_image_url ? (
            <img src={headerConfig.header_image_url} alt="School Logo" className="site-header-logo" />
          ) : (
            <span className="site-header-title">
              {headerConfig.school_name || t('layout.brand_title')}
            </span>
          )}
        </div>
        <div className="site-header-actions">
          {user && <NotificationBell />}
          <div className="header-lang-pill">
            <Globe size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <select
              value={locale}
              onChange={(e) => setLocale(e.target.value as any)}
              aria-label={t('layout.select_language')}
              className="header-lang-select"
            >
              {availableLocales.map((loc) => (
                <option key={loc} value={loc} style={{ backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}>
                  {LOCALE_NAMES[loc] || loc.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      {/* Floating Navigation Panel / Drawer */}
      {menuOpen && (
        <>
          <div className="menu-backdrop" onClick={() => setMenuOpen(false)} />
          <nav className="floating-nav-panel" aria-label={t('layout.toggle_menu')}>
            <div className="bubble-nav">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
                  onClick={() => setMenuOpen(false)}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Link>
              ))}
              <hr style={{ margin: '0.5rem 0', border: 'none', borderTop: '1px solid var(--border-color)' }} />
              <div style={{ padding: '0.5rem 0.75rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Globe size={14} /> {t('settings.section_language')}
                </span>
                <select
                  value={locale}
                  onChange={(e) => setLocale(e.target.value as any)}
                  aria-label={t('layout.language_menu')}
                  style={{
                    width: '100%',
                    padding: '0.4rem 0.5rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-color)',
                    color: 'var(--text-color)',
                    fontSize: '0.85rem',
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
              <hr style={{ margin: '0.5rem 0', border: 'none', borderTop: '1px solid var(--border-color)' }} />
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  logout();
                }}
                className="nav-item text-danger"
                style={{ background: 'none', border: 'none', width: '100%', textAlign: 'left', cursor: 'pointer' }}
              >
                <LogOut size={20} />
                <span>{t('layout.logout')}</span>
              </button>
            </div>
          </nav>
        </>
      )}

      <main className="main-content">
        <div className="page-content">
          <Outlet />
        </div>
      </main>
      <FAQChatbot />
    </div>
  );
}
