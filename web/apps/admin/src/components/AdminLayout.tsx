import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useAdmin } from '../contexts/AdminContext';

export function AdminLayout() {
  const { user, logout } = useAuth();
  const { error: adminError } = useAdmin();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { path: '/admin', label: 'Dashboard', icon: '📊' },
    { path: '/admin/users', label: 'Users', icon: '👥' },
    { path: '/admin/exams', label: 'Exams', icon: '📝' },
    { path: '/admin/system', label: 'System', icon: '⚙️' },
    { path: '/admin/settings', label: 'Settings', icon: '🔧' },
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-color)' }}>
      {/* Sidebar */}
      <aside
        style={{
          width: sidebarOpen ? '260px' : '72px',
          backgroundColor: 'var(--sidebar-bg)',
          borderRight: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 0.2s ease',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
          overflow: 'hidden',
        }}
      >
        {/* Logo/Brand */}
        <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: 0 }}>
            <div style={{ width: '36px', height: '36px', backgroundColor: 'var(--primary-color)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: '1.1rem' }}>
              PE
            </div>
            {sidebarOpen && (
              <span style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--text-color)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                PlannedEducation Admin
              </span>
            )}
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            style={{ padding: '0.5rem', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', borderRadius: 'var(--radius-sm)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: '1rem 0.5rem', overflowY: 'auto' }}>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {navItems.map(item => (
              <li key={item.path} style={{ marginBottom: '0.25rem' }}>
                <NavLink
                  to={item.path}
                  style={({ isActive }) => ({
                    display: 'flex',
                    alignItems: 'center',
                    gap: sidebarOpen ? '0.75rem' : 0,
                    padding: '0.75rem 1rem',
                    borderRadius: 'var(--radius-md)',
                    color: isActive ? 'var(--primary-color)' : 'var(--text-color)',
                    backgroundColor: isActive ? 'var(--primary-color-light, rgba(59, 130, 246, 0.1))' : 'transparent',
                    textDecoration: 'none',
                    fontWeight: isActive ? 600 : 400,
                    fontSize: '0.95rem',
                    transition: 'all 0.15s',
                    justifyContent: sidebarOpen ? 'flex-start' : 'center',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                  })}
                  title={sidebarOpen ? undefined : item.label}
                >
                  <span style={{ fontSize: '1.2rem', flexShrink: 0 }}>{item.icon}</span>
                  {sidebarOpen && <span>{item.label}</span>}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* User Info & Logout */}
        <div style={{ padding: '1rem 0.5rem', borderTop: '1px solid var(--border-color)' }}>
          {sidebarOpen && user && (
            <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-color)', marginBottom: '0.25rem' }}>
                {user.full_name || user.username}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                {user.role}
              </div>
            </div>
          )}
          <button
            onClick={handleLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: sidebarOpen ? '0.75rem' : 0,
              padding: '0.75rem 1rem',
              borderRadius: 'var(--radius-md)',
              color: '#ef4444',
              backgroundColor: 'transparent',
              border: '1px solid #ef4444',
              cursor: 'pointer',
              fontWeight: 500,
              fontSize: '0.9rem',
              width: '100%',
              justifyContent: sidebarOpen ? 'flex-start' : 'center',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              transition: 'all 0.15s',
            }}
            title={sidebarOpen ? undefined : 'Logout'}
          >
            <span style={{ fontSize: '1.1rem' }}>🚪</span>
            {sidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main
        style={{
          flex: 1,
          marginLeft: sidebarOpen ? '260px' : '72px',
          transition: 'margin-left 0.2s ease',
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Top Bar */}
        <header style={{ padding: '1rem 2rem', backgroundColor: 'var(--sidebar-bg)', borderBottom: '1px solid var(--border-color)', position: 'sticky', top: 0, zIndex: 50 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', maxWidth: '1400px', margin: '0 auto' }}>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-color)' }}>Admin Dashboard</h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              {adminError && (
                <div style={{ padding: '0.5rem 1rem', backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius-md)', color: '#dc2626', fontSize: '0.85rem' }}>
                  {adminError}
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div style={{ flex: 1, padding: '2rem', maxWidth: '1400px', margin: '0 auto', width: '100%' }}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}