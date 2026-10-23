import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, Home, Settings, GraduationCap, LogOut, BookOpen, Users, BrainCircuit, Globe, ArrowLeft, Plus, Shield } from 'lucide-react';
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
  const { logout } = useAuth();
  const { locale, setLocale, availableLocales, t } = useI18n();
  const location = useLocation();
  const navigate = useNavigate();
  const [headerConfig, setHeaderConfig] = useState<DeploymentConfig>({});

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  // Load header config for custom school branding
  useEffect(() => {
    const loadHeaderConfig = async () => {
      try {
        const res = await apiClient.get<DeploymentConfig>('/admin/config');
        setHeaderConfig(res.data);
      } catch {
        // Config may not be accessible, use defaults
      }
    };
    loadHeaderConfig();
  }, []);

  // Role-based navigation: admins can access everything, others get role-appropriate menus
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

    /* Admins see everything
    if (user?.is_admin) {
      return baseItems;
    }

    // Filter by user role
    const userRole = user?.role;
    return baseItems.filter(item => !item.roles || !userRole || item.roles.includes(userRole));
    */
    return baseItems;
  };

  const navItems = getNavItems();

  // Back navigation: go up one level in menu hierarchy
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
      navigate('/');
    }
  };

  // Render custom header
  const renderHeader = () => {
    const mode = headerConfig.header_mode || 'text';
    const schoolName = headerConfig.school_name || t('layout.brand_title');
    const imageUrl = headerConfig.header_image_url;

    if (mode === 'none') return null;

    if (mode === 'image' && imageUrl) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <img src={imageUrl} alt="School Logo" style={{ width: '32px', height: '32px', borderRadius: '4px' }} />
          <span style={{ fontWeight: 600, fontSize: '1.1rem', color: 'var(--text-color)' }}>{schoolName}</span>
        </div>
      );
    }

    // Text mode (default)
    return (
      <div className="brand-title">{schoolName}</div>
    );
  };

  return (
    <div className="app-container">
      <WatermarkOverlay />

      <header className="floating-header">
        <button onClick={() => setMenuOpen(!menuOpen)} className="icon-btn hamburger-btn" aria-label={t('layout.toggle_menu')}>
          <Menu size={24} />
        </button>
        {renderHeader()}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
          <NotificationBell />
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', backgroundColor: 'var(--sidebar-bg)', padding: '0.25rem 0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', minWidth: 0, maxWidth: '100%' }}>
            <Globe size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <select
              value={locale}
              onChange={(e) => setLocale(e.target.value as any)}
              aria-label={t('layout.select_language')}
              className="header-lang-select"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-color)',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                outline: 'none',
                maxWidth: '130px',
                minWidth: 0,
                textOverflow: 'ellipsis',
              }}
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

      {menuOpen && (
        <>
          <div className="menu-backdrop" onClick={() => setMenuOpen(false)}></div>
          <div className="floating-menu">
            <nav className="bubble-nav">
              {navItems.map((item) => (
                <Link 
                  key={item.path}
                  to={item.path} 
                  className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Link>
              ))}
              <hr style={{ margin: '0.5rem 0', border: 'none', borderTop: '1px solid var(--border-color)' }} />
              <div style={{ padding: '0.5rem 0.75rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Globe size={14} /> Language
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
              {location.pathname !== '/' && location.pathname !== '/dashboard' && (
                <button
                  onClick={handleBack}
                  className="nav-item"
                  style={{ background: 'none', border: 'none', width: '100%', textAlign: 'left', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  <ArrowLeft size={16} />
                  <span>{t('nav.back')}</span>
                </button>
              )}
              <hr style={{ margin: '0.5rem 0', border: 'none', borderTop: '1px solid var(--border-color)' }} />
              <button onClick={logout} className="nav-item text-danger" style={{ background: 'none', border: 'none', width: '100%', textAlign: 'left', cursor: 'pointer' }}>
                <LogOut size={20} />
                <span>{t('layout.logout')}</span>
              </button>
            </nav>
          </div>
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
