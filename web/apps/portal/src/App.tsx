import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { ChatGptSessionProvider } from './contexts/ChatGptSessionContext';
import { ExamProvider } from './contexts/ExamContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { MessageIcon } from './components/MessageIcon';
import { ChatOverlay } from './components/ChatOverlay';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ResetPassword } from './pages/ResetPassword';
import { Dashboard } from './pages/Dashboard';
import { Settings } from './pages/Settings';
import { TeacherExams } from './pages/TeacherExams';
import { ExamEditor } from './pages/ExamEditor';
import { ParentDashboard } from './pages/ParentDashboard';
import { AiIntegration } from './pages/AiIntegration';
import { TeacherClasses } from './pages/TeacherClasses';
import { TakeExam } from './pages/TakeExam';
import { StudentDashboard } from './pages/StudentDashboard';
import { TeacherDashboard } from './pages/TeacherDashboard';
import { AdminDashboard } from './pages/AdminDashboard';
import { AIGradingUpload } from './pages/AIGradingUpload';

import { useEffect, useState } from 'react';

function AppProviders() {
  const [chatOpen, setChatOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/messages/direct/unread-count`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setUnreadCount(data.unread_count);
        }
      } catch {
        // silent
      }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <AuthProvider>
      <ThemeProvider>
        <ToastProvider>
          <ChatGptSessionProvider>
            <ExamProvider>
              <BrowserRouter>
                <Routes>
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  <Route path="/reset-password" element={<ResetPassword />} />
                  <Route path="/" element={<ProtectedRoute />}>
                    <Route index element={<Dashboard />} />
                    <Route path="settings" element={<Settings />} />
                    <Route path="exam" element={<StudentDashboard />} />
                    <Route path="exam/:id" element={<TakeExam />} />
                    <Route path="teacher-exams" element={<TeacherExams />} />
                    <Route path="ai-grading" element={<AIGradingUpload />} />
                    <Route path="teacher-exams/:id" element={<ExamEditor />} />
                    <Route path="teacher-dashboard/:examId" element={<TeacherDashboard />} />
                    <Route path="teacher-classes" element={<TeacherClasses />} />
                    <Route path="parent-dashboard" element={<ParentDashboard />} />
                    <Route path="ai-integrations" element={<AiIntegration />} />
                    <Route path="admin" element={<AdminDashboard />} />
                  </Route>
                </Routes>
                <MessageIcon unreadCount={unreadCount} onOpen={() => setChatOpen(true)} />
                <ChatOverlay isOpen={chatOpen} onClose={() => setChatOpen(false)} />
              </BrowserRouter>
            </ExamProvider>
          </ChatGptSessionProvider>
        </ToastProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}

function App() {
  return <AppProviders />;
}

export default App;
