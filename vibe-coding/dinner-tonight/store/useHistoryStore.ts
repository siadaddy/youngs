import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface HistoryEntry {
  id: string;
  date: string;       // YYYY-MM-DD
  menu: string;
  emoji: string;
  reason?: string;
  recipe?: string[];
  tip?: string;
}

interface HistoryState {
  entries: HistoryEntry[];
  checkedSteps: Record<string, boolean[]>; // entryId → checked[]
  favorites: string[];                      // entryId[]
  addEntry: (entry: Omit<HistoryEntry, 'id'>) => string;
  removeEntry: (id: string) => void;
  getEntryById: (id: string) => HistoryEntry | undefined;
  getThisWeekMenus: () => string[];
  setCheckedSteps: (id: string, checked: boolean[]) => void;
  toggleFavorite: (id: string) => void;
}

export const useHistoryStore = create<HistoryState>()(
  persist(
    (set, get) => ({
      entries: [],
      checkedSteps: {},
      favorites: [],
      addEntry: (entry) => {
        const id = Date.now().toString() + Math.random().toString(36).slice(2);
        set((state) => ({ entries: [{ ...entry, id }, ...state.entries] }));
        return id;
      },
      removeEntry: (id) =>
        set((state) => {
          const checkedSteps = { ...state.checkedSteps };
          delete checkedSteps[id];
          return { entries: state.entries.filter((e) => e.id !== id), checkedSteps };
        }),
      getEntryById: (id) => get().entries.find((e) => e.id === id),
      getThisWeekMenus: () => {
        const now = new Date();
        const weekStart = new Date(now);
        weekStart.setDate(now.getDate() - now.getDay());
        weekStart.setHours(0, 0, 0, 0);
        return get()
          .entries.filter((e) => new Date(e.date) >= weekStart)
          .map((e) => e.menu);
      },
      setCheckedSteps: (id, checked) =>
        set((state) => ({ checkedSteps: { ...state.checkedSteps, [id]: checked } })),
      toggleFavorite: (id) =>
        set((state) => ({
          favorites: state.favorites.includes(id)
            ? state.favorites.filter((f) => f !== id)
            : [...state.favorites, id],
        })),
    }),
    { name: 'history-storage', storage: createJSONStorage(() => AsyncStorage) }
  )
);
