import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { AdminProvider } from './contexts/AdminContext';
import { AdminLayout } from './components/AdminLayout';
import { AdminDashboard } from './pages/AdminDashboard';
import { AdminUsers } from './pages/AdminUsers';
import { AdminExams } from './pages/AdminExams';
import { AdminSystem } from './pages/AdminSystem';
import { AdminSettings } from './pages/AdminSettings';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AdminProvider>
          <Routes>
            <Route element={<AdminLayout />}>
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/admin/users" element={<AdminUsers />} />
              <Route path="/admin/exams" element={<AdminExams />} />
              <Route path="/admin/system" element={<AdminSystem />} />
              <Route path="/admin/settings" element={<AdminSettings />} />
              <Route path="/" element={<AdminDashboard />} />
            </Route>
          </Routes>
        </AdminProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
