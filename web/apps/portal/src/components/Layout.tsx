import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Menu, Moon, Sun, Home, Settings, GraduationCap } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: <Home size={20} /> },
    { path: '/exam', label: 'Take Exam', icon: <GraduationCap size={20} /> },
    { path: '/settings', label: 'Settings', icon: <Settings size={20} /> },
  ];

  return (
    <div className="app-container">
      <aside className={`sidebar ${!sidebarOpen ? 'closed' : ''}`}>
        <div className="sidebar-header">
          PlannedEducation
        </div>
        <nav className="sidebar-nav">
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
        </nav>
      </aside>

      <main className="main-content">
        <header className="header">
          <button onClick={toggleSidebar} className="icon-btn" aria-label="Toggle Menu">
            <Menu size={24} />
          </button>
          
          <div style={{ marginLeft: 'auto' }}>
            <button onClick={toggleTheme} className="icon-btn" aria-label="Toggle Theme">
              {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        </header>

        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
