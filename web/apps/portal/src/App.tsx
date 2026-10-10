import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { ChatGptSessionProvider } from './contexts/ChatGptSessionContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Settings } from './pages/Settings';
import { TeacherExams } from './pages/TeacherExams';
import { ExamEditor } from './pages/ExamEditor';
import { ParentDashboard } from './pages/ParentDashboard';
import { AiIntegration } from './pages/AiIntegration';
import { TeacherClasses } from './pages/TeacherClasses';
import { TakeExam } from './pages/TakeExam';
import { TeacherDashboard } from './pages/TeacherDashboard';
import { AdminDashboard } from './pages/AdminDashboard';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

function AppProviders() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <ToastProvider>
          <ChatGptSessionProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/" element={<ProtectedRoute />}>
                  <Route index element={<Dashboard />} />
                  <Route path="settings" element={<Settings />} />
                  <Route path="exam/:id" element={<TakeExam />} />
                  <Route path="teacher-exams" element={<TeacherExams />} />
                  <Route path="teacher-exams/:id" element={<ExamEditor />} />
                  <Route path="teacher-dashboard/:examId" element={<TeacherDashboard />} />
                  <Route path="teacher-classes" element={<TeacherClasses />} />
                  <Route path="parent-dashboard" element={<ParentDashboard />} />
                  <Route path="ai-integrations" element={<AiIntegration />} />
                  <Route path="admin" element={<AdminDashboard />} />
                </Route>
              </Routes>
            </BrowserRouter>
          </ChatGptSessionProvider>
        </ToastProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}

function App() {
  const app = <AppProviders />;
  return GOOGLE_CLIENT_ID ? (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>{app}</GoogleOAuthProvider>
  ) : app;
}

export default App;
