import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Menu, Home, Settings, GraduationCap, LogOut, BookOpen, Users, BrainCircuit } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { WatermarkOverlay } from './WatermarkOverlay';

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { logout } = useAuth();
  const location = useLocation();

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);



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
      <aside className={`sidebar ${!sidebarOpen ? 'closed' : ''}`}>
        <div className="sidebar-header">
          Planned Education
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
          <button onClick={logout} className="nav-item" style={{ background: 'none', border: 'none', width: '100%', textAlign: 'left', cursor: 'pointer', color: 'inherit' }}>
            <LogOut size={20} />
            <span>Log Out</span>
          </button>
        </nav>
      </aside>

      <main className="main-content">
        <header className="header">
          <button onClick={toggleSidebar} className="icon-btn" aria-label="Toggle Menu">
            <Menu size={24} />
          </button>
        </header>

        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

