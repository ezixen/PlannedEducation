import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Menu, Home, Settings, GraduationCap, LogOut, BookOpen, Users, BrainCircuit, Globe } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useI18n, LOCALE_NAMES } from '../contexts/I18nContext';
import { WatermarkOverlay } from './WatermarkOverlay';
import { FAQChatbot } from './FAQChatbot';
import { NotificationBell } from './NotificationBell';

export function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { logout } = useAuth();
  const { locale, setLocale, availableLocales } = useI18n();
  const location = useLocation();

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMenuOpen(false);
  }, [location.pathname]);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: <Home size={20} /> },
    { path: '/exam', label: 'Take Exam', icon: <GraduationCap size={20} /> },
    { path: '/teacher-classes', label: 'Classes', icon: <Users size={20} /> },
    { path: '/teacher-exams', label: 'Exam Editor', icon: <BookOpen size={20} /> },
    { path: '/parent-dashboard', label: 'Parent Dashboard', icon: <Users size={20} /> },
    { path: '/ai-integrations', label: 'AI Integrations', icon: <BrainCircuit size={20} /> },
    { path: '/settings', label: 'Settings', icon: <Settings size={20} /> },
  ];

  return (
    <div className="app-container">
      <WatermarkOverlay />

      <header className="floating-header">
        <button onClick={() => setMenuOpen(!menuOpen)} className="icon-btn hamburger-btn" aria-label="Toggle Menu">
          <Menu size={24} />
        </button>
        <div className="brand-title">Planned Education</div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
          <NotificationBell />
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', backgroundColor: 'var(--sidebar-bg)', padding: '0.25rem 0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', minWidth: 0, maxWidth: '100%' }}>
            <Globe size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <select
              value={locale}
              onChange={(e) => setLocale(e.target.value as any)}
              aria-label="Select Language"
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
                  aria-label="Language Selector Menu"
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
              <button onClick={logout} className="nav-item text-danger" style={{ background: 'none', border: 'none', width: '100%', textAlign: 'left', cursor: 'pointer' }}>
                <LogOut size={20} />
                <span>Log Out</span>
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
