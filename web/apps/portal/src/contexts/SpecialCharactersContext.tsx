import { createContext, useContext, useMemo, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import type { CustomCharSet } from '../components/SpecialCharactersPicker';

interface SpecialCharactersContextValue {
  customCategories: CustomCharSet[];
  setCustomCategories: (categories: CustomCharSet[]) => void;
  clearCustomCategories: () => void;
}

const SpecialCharactersContext = createContext<SpecialCharactersContextValue | undefined>(undefined);

export function SpecialCharactersProvider({ children }: { children: ReactNode }) {
  const [customCategories, setCustomCategoriesState] = useState<CustomCharSet[]>([]);

  const setCustomCategories = useCallback((categories: CustomCharSet[]) => {
    setCustomCategoriesState(Array.isArray(categories) ? categories : []);
  }, []);

  const clearCustomCategories = useCallback(() => {
    setCustomCategoriesState([]);
  }, []);

  const value = useMemo(
    () => ({ customCategories, setCustomCategories, clearCustomCategories }),
    [customCategories, setCustomCategories, clearCustomCategories],
  );

  return (
    <SpecialCharactersContext.Provider value={value}>
      {children}
    </SpecialCharactersContext.Provider>
  );
}

export function useSpecialCharacters() {
  const ctx = useContext(SpecialCharactersContext);
  if (!ctx) {
    throw new Error('useSpecialCharacters must be used within SpecialCharactersProvider');
  }
  return ctx;
}
