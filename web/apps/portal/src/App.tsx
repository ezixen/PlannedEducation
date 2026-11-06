import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { ChatGptSessionProvider } from './contexts/ChatGptSessionContext';
import { ExamProvider } from './contexts/ExamContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { MessageIcon } from './components/MessageIcon';
import { ChatOverlay } from './components/ChatOverlay';
import { SpecialCharactersPicker } from './components/SpecialCharactersPicker';
import { SpecialCharactersProvider, useSpecialCharacters } from './contexts/SpecialCharactersContext';
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
import { Messages } from './pages/Messages';

import { useEffect, useState } from 'react';

function AppChrome() {
  const [chatOpen, setChatOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const { customCategories } = useSpecialCharacters();

  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        if (!token) return;
        const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/chat/messages/direct/unread-count`, {
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
    <>
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
          <Route path="messages" element={<Messages />} />
          <Route path="admin" element={<AdminDashboard />} />
        </Route>
      </Routes>
      <MessageIcon unreadCount={unreadCount} onOpen={() => setChatOpen(true)} />
      <ChatOverlay isOpen={chatOpen} onClose={() => setChatOpen(false)} />
      <SpecialCharactersPicker customCategories={customCategories} />
    </>
  );
}

function AppProviders() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <ToastProvider>
          <ChatGptSessionProvider>
            <ExamProvider>
              <SpecialCharactersProvider>
                <BrowserRouter>
                  <AppChrome />
                </BrowserRouter>
              </SpecialCharactersProvider>
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
