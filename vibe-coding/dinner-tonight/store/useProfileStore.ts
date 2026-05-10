import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

export type AgeGroup = '아이' | '청소년' | '어른' | '노인';

export interface FamilyMember {
  id: string;
  name: string;
  ageGroup: AgeGroup;
  allergies: string[];
  preferences: string[];
}

interface ProfileState {
  members: FamilyMember[];
  addMember: (member: Omit<FamilyMember, 'id'>) => void;
  removeMember: (id: string) => void;
  updateMember: (id: string, updates: Partial<FamilyMember>) => void;
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      members: [],
      addMember: (member) =>
        set((state) => ({
          members: [
            ...state.members,
            { ...member, id: Date.now().toString() + Math.random().toString(36).slice(2) },
          ],
        })),
      removeMember: (id) =>
        set((state) => ({ members: state.members.filter((m) => m.id !== id) })),
      updateMember: (id, updates) =>
        set((state) => ({
          members: state.members.map((m) => (m.id === id ? { ...m, ...updates } : m)),
        })),
    }),
    { name: 'profile-storage', storage: createJSONStorage(() => AsyncStorage) }
  )
);
