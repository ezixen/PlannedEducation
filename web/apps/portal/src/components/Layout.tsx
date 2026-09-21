import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Menu, Home, Settings, GraduationCap, LogOut, BookOpen, Users, BrainCircuit } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { WatermarkOverlay } from './WatermarkOverlay';

export function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { logout } = useAuth();
  const location = useLocation();

  useEffect(() => {
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
    </div>
  );
}
