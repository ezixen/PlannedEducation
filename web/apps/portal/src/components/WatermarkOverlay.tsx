import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function WatermarkOverlay() {
  const { user } = useAuth();
  const location = useLocation();
  const [windowDimensions, setWindowDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  useEffect(() => {
    const handleResize = () => {
      setWindowDimensions({ width: window.innerWidth, height: window.innerHeight });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Only while actively taking an exam (not the student exam list / results).
  const onActiveExam =
    /^\/exam\/[^/]+/.test(location.pathname) || location.pathname.startsWith('/take-exam');
  if (!user || user.role !== 'student' || !onActiveExam) return null;

  // Calculate how many watermark items we need to fill the screen
  const density = 250; // pixels per watermark
  const cols = Math.ceil(windowDimensions.width / density);
  const rows = Math.ceil(windowDimensions.height / density);
  const totalWatermarks = cols * rows;

  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none', // Critical: Let clicks pass through to the exam
        zIndex: 9999, // Render on top of everything
        display: 'grid',
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gridTemplateRows: `repeat(${rows}, 1fr)`,
        overflow: 'hidden',
        opacity: 0.04, // Very faint, shouldn't distract from the exam
      }}
    >
      {Array.from({ length: totalWatermarks }).map((_, i) => (
        <div
          key={i}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
            transform: 'rotate(-45deg)', // Diagonal text
            fontSize: '1rem',
            fontWeight: 'bold',
            userSelect: 'none',
            color: 'var(--text-color)',
            whiteSpace: 'nowrap'
          }}
        >
          Student ID: {user.id}
        </div>
      ))}
    </div>
  );
}

