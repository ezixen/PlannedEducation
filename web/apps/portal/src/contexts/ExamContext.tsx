import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

interface ExamContextType {
  isExamActive: boolean;
  setExamActive: (active: boolean) => void;
}

const ExamContext = createContext<ExamContextType | undefined>(undefined);

export function ExamProvider({ children }: { children: ReactNode }) {
  const [isExamActive, setIsExamActive] = useState(false);

  // Listen for exam state changes from URL or other sources
  useEffect(() => {
    const checkExamRoute = () => {
      const path = window.location.pathname;
      // Check if we're on an exam page
      const isExamPage = path.startsWith('/exam/');
      setIsExamActive(isExamPage);
    };

    checkExamRoute();
    window.addEventListener('popstate', checkExamRoute);
    
    // Also listen for hash changes
    window.addEventListener('hashchange', checkExamRoute);

    return () => {
      window.removeEventListener('popstate', checkExamRoute);
      window.removeEventListener('hashchange', checkExamRoute);
    };
  }, []);

  return (
    <ExamContext.Provider value={{ isExamActive, setExamActive: setIsExamActive }}>
      {children}
    </ExamContext.Provider>
  );
}

export function useExam() {
  const context = useContext(ExamContext);
  if (context === undefined) {
    throw new Error('useExam must be used within an ExamProvider');
  }
  return context;
}