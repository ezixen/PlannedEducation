import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, Home, Settings, GraduationCap, LogOut, BookOpen, Users, BrainCircuit, ArrowLeft, Plus, Shield, Mail, CircleHelp } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useI18n } from '../contexts/I18nContext';
import { useExam } from '../contexts/ExamContext';
import { useSpecialCharacters } from '../contexts/SpecialCharactersContext';
import { WatermarkOverlay } from './WatermarkOverlay';
import { NotificationBell } from './NotificationBell';
import { MessageIcon } from './MessageIcon';
import { ChatOverlay } from './ChatOverlay';
import { SpecialCharactersPicker } from './SpecialCharactersPicker';
import { LanguageSelector } from './LanguageSelector';
import { apiClient, API_URL } from '../api';

interface DeploymentConfig {
  school_name?: string;
  header_mode?: 'text' | 'image' | 'none';
  header_image_url?: string | null;
}

export function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const { setExamActive } = useExam();
  const { customCategories } = useSpecialCharacters();
  const location = useLocation();
  const navigate = useNavigate();
  const [headerConfig, setHeaderConfig] = useState<DeploymentConfig>({});
  const [chatOpen, setChatOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const isTakingExam = /^\/exam\/[^/]+/.test(location.pathname);

  // Close menu on route changes; also close floating chat when leaving authenticated shell routes
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  // Keep ExamContext in sync with React Router navigations (popstate alone misses pushState)
  useEffect(() => {
    setExamActive(isTakingExam);
  }, [isTakingExam, setExamActive]);

  // Unread DM badge — only while authenticated Layout is mounted
  useEffect(() => {
    if (!user) return;
    const fetchUnread = async () => {
      try {
        const token = sessionStorage.getItem('access_token');
        if (!token) return;
        const res = await fetch(`${API_URL}/chat/messages/direct/unread-count`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setUnreadCount(data.unread_count ?? 0);
        }
      } catch {
        // silent
      }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, [user]);

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
      { path: '/messages', label: t('nav.messages'), icon: <Mail size={20} />, roles: ['student', 'teacher', 'parent', 'admin'] },
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

  const ROOT_MENU_PATHS = new Set([
    '/',
    '/dashboard',
    '/settings',
    '/exam',
    '/teacher-exams',
    '/ai-grading',
    '/teacher-classes',
    '/parent-dashboard',
    '/ai-integrations',
    '/admin',
    '/login',
    '/register',
    '/reset-password',
  ]);

  const handleBack = () => {
    const path = location.pathname;
    if (path.startsWith('/teacher-exams/')) {
      navigate('/teacher-exams');
    } else if (path.startsWith('/teacher-dashboard/')) {
      navigate('/teacher-exams');
    } else if (path.startsWith('/exam/')) {
      navigate('/exam');
    } else {
      navigate(-1);
    }
  };

  const isBackAvailable = !ROOT_MENU_PATHS.has(location.pathname) && (
    location.pathname.startsWith('/teacher-exams/') ||
    location.pathname.startsWith('/teacher-dashboard/') ||
    location.pathname.startsWith('/exam/') ||
    location.pathname.split('/').filter(Boolean).length > 1
  );

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
          {user && (
            <>
              {!isTakingExam && (
                <MessageIcon unreadCount={unreadCount} onOpen={() => setChatOpen(true)} />
              )}
              <NotificationBell />
              {!isTakingExam && (
                <SpecialCharactersPicker
                  customCategories={customCategories}
                  triggerPlacement="header"
                />
              )}
            </>
          )}
          <LanguageSelector variant="pill" />
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
              <a
                href="/help"
                target="_blank"
                rel="noopener noreferrer"
                className="nav-item"
                onClick={() => setMenuOpen(false)}
                aria-label={t('faq.open_aria')}
              >
                <CircleHelp size={20} />
                <span>{t('nav.help')}</span>
              </a>
              <hr style={{ margin: '0.5rem 0', border: 'none', borderTop: '1px solid var(--border-color)' }} />
              <div style={{ padding: '0.5rem 0.75rem' }}>
                <LanguageSelector variant="block" />
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
      {/* Authenticated-only chrome: never on /login, /register, /reset-password */}
      {!isTakingExam && <ChatOverlay isOpen={chatOpen} onClose={() => setChatOpen(false)} />}
      {isTakingExam && (
        <SpecialCharactersPicker
          customCategories={customCategories}
          triggerPlacement="exam"
        />
      )}
    </div>
  );
}
