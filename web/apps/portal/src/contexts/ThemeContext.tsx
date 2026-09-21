import React, { createContext, useContext, useEffect, useState } from 'react';

export type ThemeRadius = 'square' | 'soft' | 'round';
export type ThemeColor = 'skyward' | 'carbon_cyan' | 'enterprise_blue' | 'blush_silver' | 'matrix_green' | 'black_orange' | 'sunset_cabin' | 'aurora_night' | 'comic_stage' | 'ocean_calm';

interface ThemeContextType {
  radius: ThemeRadius;
  setRadius: (r: ThemeRadius) => void;
  color: ThemeColor;
  setColor: (c: ThemeColor) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [radius, setRadius] = useState<ThemeRadius>(() => {
    return (localStorage.getItem('pe_theme_radius') as ThemeRadius) || 'soft';
  });
  const [color, setColor] = useState<ThemeColor>(() => {
    return (localStorage.getItem('pe_theme_color') as ThemeColor) || 'skyward';
  });

  useEffect(() => {
    localStorage.setItem('pe_theme_radius', radius);
    document.documentElement.setAttribute('data-radius', radius);
  }, [radius]);

  useEffect(() => {
    localStorage.setItem('pe_theme_color', color);
    document.documentElement.setAttribute('data-theme', color);
  }, [color]);

  return (
    <ThemeContext.Provider value={{ radius, setRadius, color, setColor }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
