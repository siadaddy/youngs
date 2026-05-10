import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface FridgeState {
  ingredients: string[];
  addIngredient: (name: string) => void;
  removeIngredient: (name: string) => void;
  clearAll: () => void;
}

export const useFridgeStore = create<FridgeState>()(
  persist(
    (set, get) => ({
      ingredients: [],
      addIngredient: (name) => {
        if (get().ingredients.includes(name)) return;
        set((state) => ({ ingredients: [...state.ingredients, name] }));
      },
      removeIngredient: (name) =>
        set((state) => ({ ingredients: state.ingredients.filter((i) => i !== name) })),
      clearAll: () => set({ ingredients: [] }),
    }),
    { name: 'fridge-storage', storage: createJSONStorage(() => AsyncStorage) }
  )
);
