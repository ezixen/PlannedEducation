import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Settings } from './pages/Settings';
import { TeacherExams } from './pages/TeacherExams';
import { ExamEditor } from './pages/ExamEditor';
import { ParentDashboard } from './pages/ParentDashboard';
import { AiIntegration } from './pages/AiIntegration';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'dummy-client-id.apps.googleusercontent.com';

function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <ThemeProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              
              {/* Protected Routes inside the Layout */}
              <Route path="/" element={<ProtectedRoute />}>
                <Route index element={<Dashboard />} />
                <Route path="settings" element={<Settings />} />
                <Route path="exam" element={<div><h1>Exam Portal</h1><p>SEB Integration active.</p></div>} />
                <Route path="teacher-exams" element={<TeacherExams />} />
                <Route path="teacher-exams/:id" element={<ExamEditor />} />
                <Route path="parent-dashboard" element={<ParentDashboard />} />
                <Route path="ai-integrations" element={<AiIntegration />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </ThemeProvider>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
