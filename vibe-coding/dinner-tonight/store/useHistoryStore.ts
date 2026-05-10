import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface HistoryEntry {
  id: string;
  date: string;  // YYYY-MM-DD
  menu: string;
  emoji: string;
}

interface HistoryState {
  entries: HistoryEntry[];
  addEntry: (entry: Omit<HistoryEntry, 'id'>) => void;
  removeEntry: (id: string) => void;
  getThisWeekMenus: () => string[];
}

export const useHistoryStore = create<HistoryState>()(
  persist(
    (set, get) => ({
      entries: [],
      addEntry: (entry) =>
        set((state) => ({
          entries: [
            { ...entry, id: Date.now().toString() + Math.random().toString(36).slice(2) },
            ...state.entries,
          ],
        })),
      removeEntry: (id) =>
        set((state) => ({ entries: state.entries.filter((e) => e.id !== id) })),
      getThisWeekMenus: () => {
        const now = new Date();
        const weekStart = new Date(now);
        weekStart.setDate(now.getDate() - now.getDay());
        weekStart.setHours(0, 0, 0, 0);
        return get()
          .entries.filter((e) => new Date(e.date) >= weekStart)
          .map((e) => e.menu);
      },
    }),
    { name: 'history-storage', storage: createJSONStorage(() => AsyncStorage) }
  )
);
