# "오늘 저녁 뭐 먹지?" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** React Native + Expo 앱으로 AI 저녁 메뉴 추천 시스템 구현 (Groq API, Zustand, Expo Router 4탭)

**Architecture:** Expo Router 파일 기반 탭 네비게이션. Zustand + AsyncStorage persist로 로컬 상태 영구저장. lib/groq.ts 단일 진입점으로 AI 호출, JSON 파싱 실패 시 1회 재시도.

**Tech Stack:** React Native, Expo SDK (managed), TypeScript, Expo Router, Zustand, @react-native-async-storage/async-storage, Groq API (llama-3.3-70b-versatile), jest-expo, @testing-library/react-native

---

## 파일 맵

| 파일 | 역할 |
|------|------|
| `app/_layout.tsx` | 루트 레이아웃 (GestureHandlerRootView 래핑) |
| `app/(tabs)/_layout.tsx` | 탭 네비게이션 정의 (4개 탭) |
| `app/(tabs)/index.tsx` | 홈 화면 — 조건 선택 + AI 추천 |
| `app/(tabs)/fridge.tsx` | 냉장고 화면 — 식재료 관리 |
| `app/(tabs)/history.tsx` | 기록 화면 — 날짜별 먹은 메뉴 |
| `app/(tabs)/profile.tsx` | 프로필 화면 — 가족 구성원 설정 |
| `components/IngredientTag.tsx` | 식재료 태그 (X 버튼 포함) |
| `components/ConditionPicker.tsx` | 카테고리별 단일 선택 버튼 그룹 |
| `components/MenuCard.tsx` | AI 추천 결과 카드 (로딩/에러/결과 상태) |
| `store/useFridgeStore.ts` | 식재료 목록 Zustand store |
| `store/useProfileStore.ts` | 가족 구성원 Zustand store |
| `store/useHistoryStore.ts` | 먹은 메뉴 기록 Zustand store |
| `lib/groq.ts` | Groq API 호출 + JSON 파싱 + 재시도 |
| `constants/ingredients.ts` | 카테고리별 자주 쓰는 식재료 목록 |
| `constants/theme.ts` | 색상 상수 |
| `jest.setup.ts` | AsyncStorage 모킹 |
| `__tests__/store/useFridgeStore.test.ts` | FridgeStore 유닛 테스트 |
| `__tests__/store/useProfileStore.test.ts` | ProfileStore 유닛 테스트 |
| `__tests__/store/useHistoryStore.test.ts` | HistoryStore 유닛 테스트 |
| `__tests__/lib/groq.test.ts` | groq.ts 유닛 테스트 (fetch 모킹) |
| `__tests__/components/IngredientTag.test.tsx` | IngredientTag 컴포넌트 테스트 |
| `__tests__/components/ConditionPicker.test.tsx` | ConditionPicker 컴포넌트 테스트 |
| `__tests__/components/MenuCard.test.tsx` | MenuCard 컴포넌트 테스트 |

---

## Task 1: 프로젝트 세팅 + Expo Router 구성

**Files:**
- Create: `dinner-tonight/` (Expo 앱 전체)
- Modify: `package.json` (main 필드)
- Modify: `app.json` (scheme 추가)
- Create: `jest.setup.ts`
- Create: `.env`

- [ ] **Step 1: Expo 앱 생성**

```bash
cd /Users/youngchulyu/바이브코딩
npx create-expo-app@latest dinner-tonight --template blank-typescript
cd dinner-tonight
```

Expected: `dinner-tonight/` 폴더 생성, `App.tsx` 포함

- [ ] **Step 2: 의존성 설치**

```bash
npx expo install expo-router react-native-safe-area-context react-native-screens react-native-gesture-handler
npm install zustand
npx expo install @react-native-async-storage/async-storage
npm install --save-dev @testing-library/react-native
```

Expected: `node_modules/` 업데이트, 에러 없음

- [ ] **Step 3: package.json — main 필드 변경**

`package.json`의 `"main"` 값을 변경:

```json
{
  "main": "expo-router/entry"
}
```

- [ ] **Step 4: app.json — scheme + 앱 이름 설정**

`app.json`의 `expo` 객체에 추가:

```json
{
  "expo": {
    "name": "오늘 저녁 뭐 먹지?",
    "slug": "dinner-tonight",
    "scheme": "dinner-tonight",
    "version": "1.0.0",
    "orientation": "portrait",
    "userInterfaceStyle": "automatic"
  }
}
```

- [ ] **Step 5: jest.setup.ts 생성**

```typescript
// jest.setup.ts
import mockAsyncStorage from '@react-native-async-storage/async-storage/jest/async-storage-mock';
jest.mock('@react-native-async-storage/async-storage', () => mockAsyncStorage);
```

- [ ] **Step 6: package.json — jest 설정 추가**

`package.json`의 `"jest"` 키 아래:

```json
"jest": {
  "preset": "jest-expo",
  "setupFilesAfterFramework": ["./jest.setup.ts"],
  "transformIgnorePatterns": [
    "node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|react-navigation|@react-navigation/.*|zustand)"
  ]
}
```

- [ ] **Step 7: .env 생성**

```
EXPO_PUBLIC_GROQ_API_KEY=여기에_groq_api_key_입력
```

- [ ] **Step 8: App.tsx 삭제 (Expo Router가 대체)**

```bash
rm App.tsx
```

- [ ] **Step 9: 폴더 구조 생성**

```bash
mkdir -p app/'(tabs)' components store lib constants __tests__/store __tests__/lib __tests__/components
```

- [ ] **Step 10: 커밋**

```bash
git add .
git commit -m "feat: Expo Router + Zustand + 의존성 세팅"
```

---

## Task 2: Constants

**Files:**
- Create: `constants/theme.ts`
- Create: `constants/ingredients.ts`

- [ ] **Step 1: constants/theme.ts 작성**

```typescript
// constants/theme.ts
export const colors = {
  primary: '#FF6B35',
  dark: '#2D3436',
  accent: '#FFEAA7',
  background: '#FFFFFF',
  backgroundDark: '#1A1A2E',
  surface: '#F8F9FA',
  border: '#E0E0E0',
};
```

- [ ] **Step 2: constants/ingredients.ts 작성**

```typescript
// constants/ingredients.ts
export const INGREDIENT_CATEGORIES = ['육류', '채소', '해산물', '유제품', '기타'] as const;
export type IngredientCategory = typeof INGREDIENT_CATEGORIES[number];

export const COMMON_INGREDIENTS: Record<IngredientCategory, string[]> = {
  육류: ['소고기', '돼지고기', '닭고기', '삼겹살', '다진고기', '소세지', '베이컨'],
  채소: ['양파', '마늘', '대파', '감자', '당근', '시금치', '깻잎', '고추', '애호박', '버섯'],
  해산물: ['새우', '오징어', '조개', '고등어', '참치캔', '멸치', '게맛살'],
  유제품: ['달걀', '우유', '치즈', '버터', '요거트'],
  기타: ['두부', '김치', '라면', '쌀', '된장', '간장', '고추장', '참기름', '들기름'],
};
```

- [ ] **Step 3: 커밋**

```bash
git add constants/
git commit -m "feat: 테마 색상 + 식재료 상수 추가"
```

---

## Task 3: FridgeStore (TDD)

**Files:**
- Create: `__tests__/store/useFridgeStore.test.ts`
- Create: `store/useFridgeStore.ts`

- [ ] **Step 1: 테스트 작성**

```typescript
// __tests__/store/useFridgeStore.test.ts
import { useFridgeStore } from '../../store/useFridgeStore';

beforeEach(() => {
  useFridgeStore.setState({ ingredients: [] });
});

describe('useFridgeStore', () => {
  it('초기 상태 빈 배열', () => {
    expect(useFridgeStore.getState().ingredients).toEqual([]);
  });

  it('식재료 추가', () => {
    useFridgeStore.getState().addIngredient('양파');
    expect(useFridgeStore.getState().ingredients).toContain('양파');
  });

  it('중복 추가 방지', () => {
    useFridgeStore.getState().addIngredient('양파');
    useFridgeStore.getState().addIngredient('양파');
    expect(useFridgeStore.getState().ingredients.filter((i) => i === '양파')).toHaveLength(1);
  });

  it('식재료 삭제', () => {
    useFridgeStore.getState().addIngredient('양파');
    useFridgeStore.getState().removeIngredient('양파');
    expect(useFridgeStore.getState().ingredients).not.toContain('양파');
  });

  it('전체 삭제', () => {
    useFridgeStore.getState().addIngredient('양파');
    useFridgeStore.getState().addIngredient('당근');
    useFridgeStore.getState().clearAll();
    expect(useFridgeStore.getState().ingredients).toHaveLength(0);
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
npx jest __tests__/store/useFridgeStore.test.ts --no-coverage
```

Expected: FAIL (모듈 없음)

- [ ] **Step 3: useFridgeStore.ts 구현**

```typescript
// store/useFridgeStore.ts
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npx jest __tests__/store/useFridgeStore.test.ts --no-coverage
```

Expected: PASS (5 tests)

- [ ] **Step 5: 커밋**

```bash
git add store/useFridgeStore.ts __tests__/store/useFridgeStore.test.ts
git commit -m "feat: FridgeStore + 테스트"
```

---

## Task 4: ProfileStore (TDD)

**Files:**
- Create: `__tests__/store/useProfileStore.test.ts`
- Create: `store/useProfileStore.ts`

- [ ] **Step 1: 테스트 작성**

```typescript
// __tests__/store/useProfileStore.test.ts
import { useProfileStore } from '../../store/useProfileStore';

beforeEach(() => {
  useProfileStore.setState({ members: [] });
});

describe('useProfileStore', () => {
  it('구성원 추가', () => {
    useProfileStore.getState().addMember({
      name: '엄마',
      ageGroup: '어른',
      allergies: [],
      preferences: ['한식'],
    });
    expect(useProfileStore.getState().members).toHaveLength(1);
    expect(useProfileStore.getState().members[0].name).toBe('엄마');
  });

  it('추가된 구성원에 고유 id 부여', () => {
    useProfileStore.getState().addMember({ name: '엄마', ageGroup: '어른', allergies: [], preferences: [] });
    useProfileStore.getState().addMember({ name: '아빠', ageGroup: '어른', allergies: [], preferences: [] });
    const ids = useProfileStore.getState().members.map((m) => m.id);
    expect(ids[0]).not.toBe(ids[1]);
  });

  it('구성원 삭제', () => {
    useProfileStore.getState().addMember({ name: '엄마', ageGroup: '어른', allergies: [], preferences: [] });
    const id = useProfileStore.getState().members[0].id;
    useProfileStore.getState().removeMember(id);
    expect(useProfileStore.getState().members).toHaveLength(0);
  });

  it('구성원 업데이트', () => {
    useProfileStore.getState().addMember({ name: '엄마', ageGroup: '어른', allergies: [], preferences: [] });
    const id = useProfileStore.getState().members[0].id;
    useProfileStore.getState().updateMember(id, { allergies: ['견과류'] });
    expect(useProfileStore.getState().members[0].allergies).toContain('견과류');
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
npx jest __tests__/store/useProfileStore.test.ts --no-coverage
```

Expected: FAIL

- [ ] **Step 3: useProfileStore.ts 구현**

```typescript
// store/useProfileStore.ts
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npx jest __tests__/store/useProfileStore.test.ts --no-coverage
```

Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add store/useProfileStore.ts __tests__/store/useProfileStore.test.ts
git commit -m "feat: ProfileStore + 테스트"
```

---

## Task 5: HistoryStore (TDD)

**Files:**
- Create: `__tests__/store/useHistoryStore.test.ts`
- Create: `store/useHistoryStore.ts`

- [ ] **Step 1: 테스트 작성**

```typescript
// __tests__/store/useHistoryStore.test.ts
import { useHistoryStore } from '../../store/useHistoryStore';

beforeEach(() => {
  useHistoryStore.setState({ entries: [] });
});

describe('useHistoryStore', () => {
  it('기록 추가', () => {
    useHistoryStore.getState().addEntry({ date: '2026-05-09', menu: '된장찌개', emoji: '🍲' });
    expect(useHistoryStore.getState().entries).toHaveLength(1);
    expect(useHistoryStore.getState().entries[0].menu).toBe('된장찌개');
  });

  it('기록 삭제', () => {
    useHistoryStore.getState().addEntry({ date: '2026-05-09', menu: '된장찌개', emoji: '🍲' });
    const id = useHistoryStore.getState().entries[0].id;
    useHistoryStore.getState().removeEntry(id);
    expect(useHistoryStore.getState().entries).toHaveLength(0);
  });

  it('이번 주 메뉴 반환', () => {
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    useHistoryStore.getState().addEntry({ date: todayStr, menu: '된장찌개', emoji: '🍲' });

    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 8);
    const lastWeekStr = lastWeek.toISOString().split('T')[0];
    useHistoryStore.getState().addEntry({ date: lastWeekStr, menu: '김치찌개', emoji: '🌶️' });

    const result = useHistoryStore.getState().getThisWeekMenus();
    expect(result).toContain('된장찌개');
    expect(result).not.toContain('김치찌개');
  });

  it('이번 주 기록 없으면 빈 배열', () => {
    useHistoryStore.getState().addEntry({ date: '2020-01-01', menu: '파스타', emoji: '🍝' });
    expect(useHistoryStore.getState().getThisWeekMenus()).toHaveLength(0);
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
npx jest __tests__/store/useHistoryStore.test.ts --no-coverage
```

Expected: FAIL

- [ ] **Step 3: useHistoryStore.ts 구현**

```typescript
// store/useHistoryStore.ts
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npx jest __tests__/store/useHistoryStore.test.ts --no-coverage
```

Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add store/useHistoryStore.ts __tests__/store/useHistoryStore.test.ts
git commit -m "feat: HistoryStore + 테스트"
```

---

## Task 6: Groq API lib (TDD)

**Files:**
- Create: `__tests__/lib/groq.test.ts`
- Create: `lib/groq.ts`

- [ ] **Step 1: 테스트 작성**

```typescript
// __tests__/lib/groq.test.ts
import { getMenuRecommendation } from '../../lib/groq';

const mockMenu = {
  menu: '된장찌개',
  emoji: '🍲',
  reason: '냉장고 재료로 쉽게 만들 수 있어요.',
  recipe: ['된장과 두부를 준비합니다', '물을 끓입니다', '재료를 넣고 끓입니다'],
  tip: '국물을 진하게 우려내세요.',
  alternatives: ['김치찌개', '두부조림'],
};

const defaultInput = {
  conditions: { style: '집밥', mood: '가볍게', who: '둘이서', time: '30분' },
  ingredients: ['두부', '된장'],
  recentMenus: [],
  familyProfile: '',
};

beforeEach(() => {
  process.env.EXPO_PUBLIC_GROQ_API_KEY = 'test-key';
  global.fetch = jest.fn();
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('getMenuRecommendation', () => {
  it('정상 응답 파싱', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ choices: [{ message: { content: JSON.stringify(mockMenu) } }] }),
    });

    const result = await getMenuRecommendation(defaultInput);
    expect(result.menu).toBe('된장찌개');
    expect(result.recipe).toHaveLength(3);
    expect(result.alternatives).toHaveLength(2);
  });

  it('JSON 파싱 실패 시 1회 재시도 후 성공', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ choices: [{ message: { content: 'invalid json {{' } }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ choices: [{ message: { content: JSON.stringify(mockMenu) } }] }),
      });

    const result = await getMenuRecommendation(defaultInput);
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(result.menu).toBe('된장찌개');
  });

  it('두 번 모두 실패하면 에러 throw', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ choices: [{ message: { content: 'bad json' } }] }),
    });

    await expect(getMenuRecommendation(defaultInput)).rejects.toThrow('메뉴 추천에 실패했습니다');
  });

  it('API 키 없으면 에러 throw', async () => {
    delete process.env.EXPO_PUBLIC_GROQ_API_KEY;
    await expect(getMenuRecommendation(defaultInput)).rejects.toThrow('API 키');
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
npx jest __tests__/lib/groq.test.ts --no-coverage
```

Expected: FAIL

- [ ] **Step 3: lib/groq.ts 구현**

```typescript
// lib/groq.ts
const GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions';
const MODEL = 'llama-3.3-70b-versatile';

export interface RecommendationInput {
  conditions: { style: string; mood: string; who: string; time: string };
  ingredients: string[];
  recentMenus: string[];
  familyProfile: string;
}

export interface MenuRecommendation {
  menu: string;
  emoji: string;
  reason: string;
  recipe: [string, string, string];
  tip: string;
  alternatives: [string, string];
}

async function callGroq(input: RecommendationInput): Promise<MenuRecommendation> {
  const apiKey = process.env.EXPO_PUBLIC_GROQ_API_KEY;
  if (!apiKey) throw new Error('API 키가 설정되지 않았습니다');

  const systemPrompt = `당신은 한국 가정의 저녁 메뉴를 추천하는 전문가입니다.\n반드시 JSON 형식으로만 응답하세요.`;

  const userPrompt = `오늘 저녁 메뉴를 추천해줘.

[조건]
- 스타일: ${input.conditions.style || '미지정'}
- 기분: ${input.conditions.mood || '미지정'}
- 인원: ${input.conditions.who || '미지정'}
- 조리시간: ${input.conditions.time || '미지정'}

[냉장고 재료]
${input.ingredients.length > 0 ? input.ingredients.join(', ') : '없음'}

[이번 주 먹은 메뉴] (제외해줘)
${input.recentMenus.length > 0 ? input.recentMenus.join(', ') : '없음'}

[가족 정보]
${input.familyProfile || '없음'}

JSON 형식으로만 응답:
{
  "menu": "메뉴명",
  "emoji": "이모지",
  "reason": "추천 이유 1문장",
  "recipe": ["1단계", "2단계", "3단계"],
  "tip": "꿀팁 1문장",
  "alternatives": ["대안메뉴1", "대안메뉴2"]
}`;

  const response = await fetch(GROQ_API_URL, {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: MODEL,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      response_format: { type: 'json_object' },
      temperature: 0.8,
    }),
  });

  if (!response.ok) throw new Error(`Groq API 오류: ${response.status}`);
  const data = await response.json();
  return JSON.parse(data.choices[0].message.content) as MenuRecommendation;
}

export async function getMenuRecommendation(input: RecommendationInput): Promise<MenuRecommendation> {
  try {
    return await callGroq(input);
  } catch (firstErr: any) {
    if (firstErr.message.includes('API 키')) throw firstErr;
    try {
      return await callGroq(input);
    } catch {
      throw new Error('메뉴 추천에 실패했습니다. 다시 시도해주세요.');
    }
  }
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npx jest __tests__/lib/groq.test.ts --no-coverage
```

Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add lib/groq.ts __tests__/lib/groq.test.ts
git commit -m "feat: Groq API 연동 + 재시도 로직 + 테스트"
```

---

## Task 7: IngredientTag 컴포넌트

**Files:**
- Create: `__tests__/components/IngredientTag.test.tsx`
- Create: `components/IngredientTag.tsx`

- [ ] **Step 1: 테스트 작성**

```typescript
// __tests__/components/IngredientTag.test.tsx
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { IngredientTag } from '../../components/IngredientTag';

describe('IngredientTag', () => {
  it('이름 렌더링', () => {
    const { getByText } = render(<IngredientTag name="양파" onRemove={() => {}} />);
    expect(getByText('양파')).toBeTruthy();
  });

  it('X 버튼 클릭 시 onRemove(name) 호출', () => {
    const onRemove = jest.fn();
    const { getByTestId } = render(<IngredientTag name="양파" onRemove={onRemove} />);
    fireEvent.press(getByTestId('remove-button'));
    expect(onRemove).toHaveBeenCalledWith('양파');
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
npx jest __tests__/components/IngredientTag.test.tsx --no-coverage
```

Expected: FAIL

- [ ] **Step 3: components/IngredientTag.tsx 구현**

```typescript
// components/IngredientTag.tsx
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors } from '../constants/theme';

interface Props {
  name: string;
  onRemove: (name: string) => void;
}

export function IngredientTag({ name, onRemove }: Props) {
  return (
    <View style={styles.tag}>
      <Text style={styles.name}>{name}</Text>
      <TouchableOpacity
        testID="remove-button"
        onPress={() => onRemove(name)}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <Text style={styles.x}>×</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  tag: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.accent,
    borderRadius: 20,
    paddingVertical: 6,
    paddingLeft: 12,
    paddingRight: 8,
    margin: 4,
  },
  name: { fontSize: 14, color: colors.dark, marginRight: 4 },
  x: { fontSize: 18, color: colors.dark, lineHeight: 20 },
});
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npx jest __tests__/components/IngredientTag.test.tsx --no-coverage
```

Expected: PASS (2 tests)

- [ ] **Step 5: 커밋**

```bash
git add components/IngredientTag.tsx __tests__/components/IngredientTag.test.tsx
git commit -m "feat: IngredientTag 컴포넌트 + 테스트"
```

---

## Task 8: ConditionPicker 컴포넌트

**Files:**
- Create: `__tests__/components/ConditionPicker.test.tsx`
- Create: `components/ConditionPicker.tsx`

- [ ] **Step 1: 테스트 작성**

```typescript
// __tests__/components/ConditionPicker.test.tsx
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { ConditionPicker } from '../../components/ConditionPicker';

const OPTIONS = ['집밥', '배달', '외식'];

describe('ConditionPicker', () => {
  it('레이블 + 옵션 렌더링', () => {
    const { getByText } = render(
      <ConditionPicker label="스타일" options={OPTIONS} value={null} onChange={() => {}} />
    );
    expect(getByText('스타일')).toBeTruthy();
    expect(getByText('집밥')).toBeTruthy();
    expect(getByText('배달')).toBeTruthy();
  });

  it('옵션 선택 시 onChange 호출', () => {
    const onChange = jest.fn();
    const { getByText } = render(
      <ConditionPicker label="스타일" options={OPTIONS} value={null} onChange={onChange} />
    );
    fireEvent.press(getByText('집밥'));
    expect(onChange).toHaveBeenCalledWith('집밥');
  });

  it('선택된 옵션 재클릭 시 onChange 재호출', () => {
    const onChange = jest.fn();
    const { getByText } = render(
      <ConditionPicker label="스타일" options={OPTIONS} value="배달" onChange={onChange} />
    );
    fireEvent.press(getByText('배달'));
    expect(onChange).toHaveBeenCalledWith('배달');
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
npx jest __tests__/components/ConditionPicker.test.tsx --no-coverage
```

Expected: FAIL

- [ ] **Step 3: components/ConditionPicker.tsx 구현**

```typescript
// components/ConditionPicker.tsx
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { colors } from '../constants/theme';

interface Props {
  label: string;
  options: string[];
  value: string | null;
  onChange: (value: string) => void;
}

export function ConditionPicker({ label, options, value, onChange }: Props) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        {options.map((option) => (
          <TouchableOpacity
            key={option}
            style={[styles.option, value === option && styles.selected]}
            onPress={() => onChange(option)}
          >
            <Text style={[styles.optionText, value === option && styles.selectedText]}>
              {option}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginVertical: 8 },
  label: { fontSize: 14, fontWeight: '600', color: colors.dark, marginBottom: 8 },
  option: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: colors.border,
    marginRight: 8,
    backgroundColor: colors.surface,
  },
  selected: { backgroundColor: colors.primary, borderColor: colors.primary },
  optionText: { fontSize: 14, color: colors.dark },
  selectedText: { color: '#FFFFFF', fontWeight: '600' },
});
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npx jest __tests__/components/ConditionPicker.test.tsx --no-coverage
```

Expected: PASS (3 tests)

- [ ] **Step 5: 커밋**

```bash
git add components/ConditionPicker.tsx __tests__/components/ConditionPicker.test.tsx
git commit -m "feat: ConditionPicker 컴포넌트 + 테스트"
```

---

## Task 9: MenuCard 컴포넌트

**Files:**
- Create: `__tests__/components/MenuCard.test.tsx`
- Create: `components/MenuCard.tsx`

- [ ] **Step 1: 테스트 작성**

```typescript
// __tests__/components/MenuCard.test.tsx
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { MenuCard } from '../../components/MenuCard';
import { MenuRecommendation } from '../../lib/groq';

const mockMenu: MenuRecommendation = {
  menu: '된장찌개',
  emoji: '🍲',
  reason: '재료가 다 있어요.',
  recipe: ['된장 준비', '물 끓이기', '재료 투입'],
  tip: '국물 진하게!',
  alternatives: ['김치찌개', '두부조림'],
};

describe('MenuCard', () => {
  it('로딩 중 인디케이터 표시', () => {
    const { getByTestId } = render(
      <MenuCard loading recommendation={null} error={null} onConfirm={() => {}} onRetry={() => {}} />
    );
    expect(getByTestId('loading-indicator')).toBeTruthy();
  });

  it('에러 메시지 표시', () => {
    const { getByText } = render(
      <MenuCard loading={false} recommendation={null} error="네트워크 오류" onConfirm={() => {}} onRetry={() => {}} />
    );
    expect(getByText('네트워크 오류')).toBeTruthy();
  });

  it('추천 결과 — 메뉴명·이유·레시피·꿀팁 렌더링', () => {
    const { getByText } = render(
      <MenuCard loading={false} recommendation={mockMenu} error={null} onConfirm={() => {}} onRetry={() => {}} />
    );
    expect(getByText('된장찌개')).toBeTruthy();
    expect(getByText('재료가 다 있어요.')).toBeTruthy();
    expect(getByText('1. 된장 준비')).toBeTruthy();
    expect(getByText('💡 국물 진하게!')).toBeTruthy();
  });

  it('"이 메뉴로 결정!" 클릭 시 onConfirm 호출', () => {
    const onConfirm = jest.fn();
    const { getByText } = render(
      <MenuCard loading={false} recommendation={mockMenu} error={null} onConfirm={onConfirm} onRetry={() => {}} />
    );
    fireEvent.press(getByText('이 메뉴로 결정!'));
    expect(onConfirm).toHaveBeenCalled();
  });

  it('"다시 추천" 클릭 시 onRetry 호출', () => {
    const onRetry = jest.fn();
    const { getByText } = render(
      <MenuCard loading={false} recommendation={mockMenu} error={null} onConfirm={() => {}} onRetry={onRetry} />
    );
    fireEvent.press(getByText('다시 추천'));
    expect(onRetry).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
npx jest __tests__/components/MenuCard.test.tsx --no-coverage
```

Expected: FAIL

- [ ] **Step 3: components/MenuCard.tsx 구현**

```typescript
// components/MenuCard.tsx
import React from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, useColorScheme,
} from 'react-native';
import { colors } from '../constants/theme';
import { MenuRecommendation } from '../lib/groq';

interface Props {
  loading: boolean;
  recommendation: MenuRecommendation | null;
  error: string | null;
  onConfirm: () => void;
  onRetry: () => void;
}

export function MenuCard({ loading, recommendation, error, onConfirm, onRetry }: Props) {
  const isDark = useColorScheme() === 'dark';
  const cardBg = isDark ? '#2d2d2d' : colors.background;
  const textColor = isDark ? '#FFFFFF' : colors.dark;

  if (loading) {
    return (
      <View style={[styles.card, { backgroundColor: cardBg }]}>
        <ActivityIndicator testID="loading-indicator" size="large" color={colors.primary} />
        <Text style={[styles.loadingText, { color: textColor }]}>AI가 고민 중...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={[styles.card, { backgroundColor: cardBg }]}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={onRetry}>
          <Text style={styles.retryText}>다시 시도</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!recommendation) return null;

  const { menu, emoji, reason, recipe, tip, alternatives } = recommendation;

  return (
    <View style={[styles.card, { backgroundColor: cardBg }]}>
      <Text style={styles.emoji}>{emoji}</Text>
      <Text style={[styles.menuName, { color: textColor }]}>{menu}</Text>
      <Text style={[styles.reason, { color: textColor }]}>{reason}</Text>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: textColor }]}>🍳 레시피</Text>
        {recipe.map((step, i) => (
          <Text key={i} style={[styles.step, { color: textColor }]}>{`${i + 1}. ${step}`}</Text>
        ))}
      </View>

      <View style={[styles.tipBox, { backgroundColor: colors.accent }]}>
        <Text style={styles.tipText}>💡 {tip}</Text>
      </View>

      <Text style={[styles.altTitle, { color: textColor }]}>대안 메뉴</Text>
      <View style={styles.altRow}>
        {alternatives.map((alt) => (
          <View key={alt} style={styles.altTag}>
            <Text style={styles.altText}>{alt}</Text>
          </View>
        ))}
      </View>

      <TouchableOpacity style={styles.confirmBtn} onPress={onConfirm}>
        <Text style={styles.confirmText}>이 메뉴로 결정!</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.retryBtn} onPress={onRetry}>
        <Text style={styles.retryText}>다시 추천</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16, padding: 24, margin: 16,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08, shadowRadius: 8, elevation: 3, alignItems: 'center',
  },
  emoji: { fontSize: 64, marginBottom: 8 },
  menuName: { fontSize: 28, fontWeight: '700', marginBottom: 8 },
  reason: { fontSize: 16, textAlign: 'center', marginBottom: 16, opacity: 0.8 },
  section: { alignSelf: 'stretch', marginBottom: 16 },
  sectionTitle: { fontSize: 16, fontWeight: '600', marginBottom: 8 },
  step: { fontSize: 14, marginBottom: 4, lineHeight: 22 },
  tipBox: { borderRadius: 12, padding: 12, marginBottom: 16, alignSelf: 'stretch' },
  tipText: { fontSize: 14, color: colors.dark },
  altTitle: { fontSize: 14, fontWeight: '600', marginBottom: 8 },
  altRow: { flexDirection: 'row', marginBottom: 20 },
  altTag: {
    backgroundColor: colors.surface, borderRadius: 12,
    paddingVertical: 6, paddingHorizontal: 12, marginHorizontal: 4,
    borderWidth: 1, borderColor: colors.border,
  },
  altText: { fontSize: 13, color: colors.dark },
  confirmBtn: {
    backgroundColor: colors.primary, borderRadius: 12,
    paddingVertical: 14, alignSelf: 'stretch', alignItems: 'center', marginBottom: 10,
  },
  confirmText: { color: '#FFFFFF', fontSize: 17, fontWeight: '700' },
  retryBtn: {
    borderRadius: 12, paddingVertical: 12,
    borderWidth: 1.5, borderColor: colors.border,
    alignSelf: 'stretch', alignItems: 'center',
  },
  retryText: { color: colors.dark, fontSize: 15 },
  loadingText: { marginTop: 16, fontSize: 16 },
  errorText: { color: '#e74c3c', fontSize: 16, marginBottom: 16, textAlign: 'center' },
});
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npx jest __tests__/components/MenuCard.test.tsx --no-coverage
```

Expected: PASS (5 tests)

- [ ] **Step 5: 커밋**

```bash
git add components/MenuCard.tsx __tests__/components/MenuCard.test.tsx
git commit -m "feat: MenuCard 컴포넌트 + 테스트"
```

---

## Task 10: App Layout + Tab Navigation

**Files:**
- Create: `app/_layout.tsx`
- Create: `app/(tabs)/_layout.tsx`

- [ ] **Step 1: app/_layout.tsx 작성**

```typescript
// app/_layout.tsx
import { Stack } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <Stack screenOptions={{ headerShown: false }} />
    </GestureHandlerRootView>
  );
}
```

- [ ] **Step 2: app/(tabs)/_layout.tsx 작성**

```typescript
// app/(tabs)/_layout.tsx
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../constants/theme';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

function tabIcon(name: IconName) {
  return ({ color, size }: { color: string; size: number }) => (
    <Ionicons name={name} size={size} color={color} />
  );
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: '#636e72',
        headerShown: false,
      }}
    >
      <Tabs.Screen name="index" options={{ title: '추천', tabBarIcon: tabIcon('restaurant') }} />
      <Tabs.Screen name="fridge" options={{ title: '냉장고', tabBarIcon: tabIcon('grid') }} />
      <Tabs.Screen name="history" options={{ title: '기록', tabBarIcon: tabIcon('time') }} />
      <Tabs.Screen name="profile" options={{ title: '프로필', tabBarIcon: tabIcon('people') }} />
    </Tabs>
  );
}
```

- [ ] **Step 3: 앱 기동 확인**

```bash
npx expo start
```

Expected: Metro 서버 실행, QR 코드 표시. Expo Go 앱으로 스캔 시 빈 탭 화면 표시.

- [ ] **Step 4: 커밋**

```bash
git add app/
git commit -m "feat: 루트 레이아웃 + 탭 네비게이션 구성"
```

---

## Task 11: 홈 화면 (index.tsx)

**Files:**
- Create: `app/(tabs)/index.tsx`

- [ ] **Step 1: app/(tabs)/index.tsx 작성**

```typescript
// app/(tabs)/index.tsx
import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, useColorScheme, SafeAreaView,
} from 'react-native';
import { ConditionPicker } from '../../components/ConditionPicker';
import { MenuCard } from '../../components/MenuCard';
import { useFridgeStore } from '../../store/useFridgeStore';
import { useProfileStore } from '../../store/useProfileStore';
import { useHistoryStore } from '../../store/useHistoryStore';
import { getMenuRecommendation, MenuRecommendation } from '../../lib/groq';
import { colors } from '../../constants/theme';

const CONDITIONS = {
  style: ['집밥', '배달', '외식'],
  mood: ['가볍게', '든든하게', '특별하게'],
  who: ['혼자', '둘이서', '온 가족'],
  time: ['15분 이내', '30분', '여유있게'],
};

export default function HomeScreen() {
  const isDark = useColorScheme() === 'dark';

  const [style, setStyle] = useState<string | null>(null);
  const [mood, setMood] = useState<string | null>(null);
  const [who, setWho] = useState<string | null>(null);
  const [time, setTime] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<MenuRecommendation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ingredients = useFridgeStore((s) => s.ingredients);
  const members = useProfileStore((s) => s.members);
  const { getThisWeekMenus, addEntry } = useHistoryStore();

  const hasCondition = !!(style || mood || who || time);

  const familyProfile = members.length > 0
    ? members
        .map((m) => `${m.name}(${m.ageGroup}, 알레르기: ${m.allergies.join('/') || '없음'})`)
        .join(', ')
    : '';

  async function handleRecommend() {
    setLoading(true);
    setError(null);
    setRecommendation(null);
    try {
      const result = await getMenuRecommendation({
        conditions: { style: style ?? '', mood: mood ?? '', who: who ?? '', time: time ?? '' },
        ingredients,
        recentMenus: getThisWeekMenus(),
        familyProfile,
      });
      setRecommendation(result);
    } catch (e: any) {
      setError(e.message ?? '다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  }

  function handleConfirm() {
    if (!recommendation) return;
    addEntry({
      date: new Date().toISOString().split('T')[0],
      menu: recommendation.menu,
      emoji: recommendation.emoji,
    });
    setRecommendation(null);
    setStyle(null); setMood(null); setWho(null); setTime(null);
  }

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: isDark ? colors.backgroundDark : '#F5F5F5' }]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={[styles.title, { color: isDark ? '#FFF' : colors.dark }]}>오늘 저녁 뭐 먹지? 🍽️</Text>

        <View style={[styles.card, { backgroundColor: isDark ? '#2d2d2d' : '#FFF' }]}>
          <ConditionPicker label="스타일" options={CONDITIONS.style} value={style} onChange={setStyle} />
          <ConditionPicker label="기분" options={CONDITIONS.mood} value={mood} onChange={setMood} />
          <ConditionPicker label="인원" options={CONDITIONS.who} value={who} onChange={setWho} />
          <ConditionPicker label="조리시간" options={CONDITIONS.time} value={time} onChange={setTime} />
          {ingredients.length > 0 && (
            <Text style={styles.fridgeNote}>🧊 냉장고 재료 {ingredients.length}개 반영됨</Text>
          )}
        </View>

        <TouchableOpacity
          style={[styles.recommendBtn, (!hasCondition || loading) && styles.disabled]}
          onPress={handleRecommend}
          disabled={!hasCondition || loading}
        >
          <Text style={styles.recommendText}>추천받기 ✨</Text>
        </TouchableOpacity>

        {(loading || recommendation || error) && (
          <MenuCard
            loading={loading}
            recommendation={recommendation}
            error={error}
            onConfirm={handleConfirm}
            onRetry={handleRecommend}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  scroll: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 26, fontWeight: '800', marginBottom: 20, marginTop: 8 },
  card: {
    borderRadius: 16, padding: 16, marginBottom: 16,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06, shadowRadius: 4, elevation: 2,
  },
  fridgeNote: { marginTop: 12, fontSize: 13, color: colors.primary, fontWeight: '500' },
  recommendBtn: {
    backgroundColor: colors.primary, borderRadius: 14,
    paddingVertical: 16, alignItems: 'center',
  },
  disabled: { opacity: 0.4 },
  recommendText: { color: '#FFFFFF', fontSize: 18, fontWeight: '700' },
});
```

- [ ] **Step 2: Expo Go에서 홈 화면 확인**

Expo Go 앱 실행 → 홈 탭에서:
- 4개 카테고리 조건 선택 버튼 표시 확인
- 선택 시 주황색으로 하이라이트 확인
- "추천받기" 버튼 비활성(조건 미선택) / 활성(조건 선택) 상태 확인
- GROQ_API_KEY 설정 후 추천 버튼 클릭 → MenuCard 로딩 → 결과 확인

- [ ] **Step 3: 커밋**

```bash
git add app/'(tabs)'/index.tsx
git commit -m "feat: 홈 화면 — 조건 선택 + AI 추천 + MenuCard 연동"
```

---

## Task 12: 냉장고 화면 (fridge.tsx)

**Files:**
- Create: `app/(tabs)/fridge.tsx`

- [ ] **Step 1: app/(tabs)/fridge.tsx 작성**

```typescript
// app/(tabs)/fridge.tsx
import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity,
  useColorScheme, SafeAreaView,
} from 'react-native';
import { IngredientTag } from '../../components/IngredientTag';
import { useFridgeStore } from '../../store/useFridgeStore';
import { COMMON_INGREDIENTS, INGREDIENT_CATEGORIES, IngredientCategory } from '../../constants/ingredients';
import { colors } from '../../constants/theme';

export default function FridgeScreen() {
  const isDark = useColorScheme() === 'dark';
  const [activeCategory, setActiveCategory] = useState<IngredientCategory>('채소');
  const [customInput, setCustomInput] = useState('');
  const { ingredients, addIngredient, removeIngredient } = useFridgeStore();

  function handleAddCustom() {
    const trimmed = customInput.trim();
    if (trimmed) { addIngredient(trimmed); setCustomInput(''); }
  }

  const cardBg = isDark ? '#2d2d2d' : '#FFF';
  const textColor = isDark ? '#FFF' : colors.dark;

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: isDark ? colors.backgroundDark : '#F5F5F5' }]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={[styles.title, { color: textColor }]}>🧊 내 냉장고</Text>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryRow}>
          {INGREDIENT_CATEGORIES.map((cat) => (
            <TouchableOpacity
              key={cat}
              style={[styles.catBtn, activeCategory === cat && styles.catActive]}
              onPress={() => setActiveCategory(cat)}
            >
              <Text style={[styles.catText, activeCategory === cat && styles.catActiveText]}>{cat}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <View style={[styles.card, { backgroundColor: cardBg }]}>
          <Text style={[styles.subTitle, { color: textColor }]}>빠른 추가</Text>
          <View style={styles.quickGrid}>
            {COMMON_INGREDIENTS[activeCategory].map((item) => {
              const isAdded = ingredients.includes(item);
              return (
                <TouchableOpacity
                  key={item}
                  style={[styles.quickBtn, isAdded && styles.quickBtnAdded]}
                  onPress={() => isAdded ? removeIngredient(item) : addIngredient(item)}
                >
                  <Text style={[styles.quickText, isAdded && styles.quickTextAdded]}>{item}</Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <View style={styles.inputRow}>
            <TextInput
              style={[styles.input, { color: textColor, borderColor: colors.border }]}
              value={customInput}
              onChangeText={setCustomInput}
              placeholder="직접 입력..."
              placeholderTextColor="#aaa"
              onSubmitEditing={handleAddCustom}
              returnKeyType="done"
            />
            <TouchableOpacity style={styles.addBtn} onPress={handleAddCustom}>
              <Text style={styles.addBtnText}>추가</Text>
            </TouchableOpacity>
          </View>
        </View>

        {ingredients.length > 0 && (
          <View style={[styles.card, { backgroundColor: cardBg }]}>
            <Text style={[styles.subTitle, { color: textColor }]}>등록된 재료 ({ingredients.length})</Text>
            <View style={styles.tagRow}>
              {ingredients.map((item) => (
                <IngredientTag key={item} name={item} onRemove={removeIngredient} />
              ))}
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  scroll: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: '800', marginBottom: 16 },
  categoryRow: { marginBottom: 12 },
  catBtn: {
    paddingVertical: 8, paddingHorizontal: 16, borderRadius: 20,
    borderWidth: 1.5, borderColor: colors.border, marginRight: 8, backgroundColor: '#FFF',
  },
  catActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  catText: { fontSize: 14, color: colors.dark },
  catActiveText: { color: '#FFF', fontWeight: '600' },
  card: {
    borderRadius: 16, padding: 16, marginBottom: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06, shadowRadius: 4, elevation: 2,
  },
  subTitle: { fontSize: 15, fontWeight: '600', marginBottom: 10 },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 12 },
  quickBtn: {
    paddingVertical: 8, paddingHorizontal: 14, borderRadius: 20,
    borderWidth: 1.5, borderColor: colors.border, margin: 4, backgroundColor: '#FFF',
  },
  quickBtnAdded: { backgroundColor: colors.primary, borderColor: colors.primary },
  quickText: { fontSize: 14, color: colors.dark },
  quickTextAdded: { color: '#FFF', fontWeight: '600' },
  inputRow: { flexDirection: 'row' },
  input: {
    flex: 1, borderRadius: 12, paddingHorizontal: 14,
    paddingVertical: 12, fontSize: 15, borderWidth: 1.5, marginRight: 8,
  },
  addBtn: { backgroundColor: colors.primary, borderRadius: 12, paddingHorizontal: 20, justifyContent: 'center' },
  addBtnText: { color: '#FFF', fontWeight: '700', fontSize: 15 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap' },
});
```

- [ ] **Step 2: Expo Go에서 냉장고 화면 확인**

- 카테고리 탭 전환 시 재료 목록 변경 확인
- 재료 탭 클릭 → 추가(주황) / 재클릭 → 삭제 확인
- 직접 입력 → "추가" 버튼 클릭 → 태그 표시 확인
- X 버튼으로 태그 삭제 확인
- 앱 재시작 후 재료 유지 (AsyncStorage persist) 확인

- [ ] **Step 3: 커밋**

```bash
git add app/'(tabs)'/fridge.tsx
git commit -m "feat: 냉장고 화면 — 카테고리별 식재료 관리"
```

---

## Task 13: 기록 화면 (history.tsx)

**Files:**
- Create: `app/(tabs)/history.tsx`

- [ ] **Step 1: app/(tabs)/history.tsx 작성**

```typescript
// app/(tabs)/history.tsx
import React from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  useColorScheme, SafeAreaView, Alert,
} from 'react-native';
import { useHistoryStore, HistoryEntry } from '../../store/useHistoryStore';
import { colors } from '../../constants/theme';

export default function HistoryScreen() {
  const isDark = useColorScheme() === 'dark';
  const { entries, removeEntry } = useHistoryStore();
  const sorted = [...entries].sort((a, b) => b.date.localeCompare(a.date));

  function handleDelete(entry: HistoryEntry) {
    Alert.alert('삭제', `"${entry.menu}" 기록을 삭제할까요?`, [
      { text: '취소', style: 'cancel' },
      { text: '삭제', style: 'destructive', onPress: () => removeEntry(entry.id) },
    ]);
  }

  function renderItem({ item }: { item: HistoryEntry }) {
    return (
      <View style={[styles.item, { backgroundColor: isDark ? '#2d2d2d' : '#FFF' }]}>
        <Text style={styles.emoji}>{item.emoji}</Text>
        <View style={styles.info}>
          <Text style={[styles.menuName, { color: isDark ? '#FFF' : colors.dark }]}>{item.menu}</Text>
          <Text style={styles.date}>{item.date}</Text>
        </View>
        <TouchableOpacity onPress={() => handleDelete(item)} style={styles.deleteBtn}>
          <Text style={styles.deleteText}>삭제</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: isDark ? colors.backgroundDark : '#F5F5F5' }]}>
      <Text style={[styles.title, { color: isDark ? '#FFF' : colors.dark }]}>📅 먹은 메뉴 기록</Text>
      {sorted.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyText}>아직 기록이 없어요.</Text>
          <Text style={styles.emptyText}>홈에서 메뉴를 결정해보세요!</Text>
        </View>
      ) : (
        <FlatList
          data={sorted}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  title: { fontSize: 24, fontWeight: '800', margin: 16 },
  list: { padding: 16, paddingTop: 0 },
  item: {
    flexDirection: 'row', alignItems: 'center', borderRadius: 14,
    padding: 14, marginBottom: 10,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
  },
  emoji: { fontSize: 32, marginRight: 12 },
  info: { flex: 1 },
  menuName: { fontSize: 17, fontWeight: '600', marginBottom: 4 },
  date: { fontSize: 13, color: '#888' },
  deleteBtn: { padding: 8 },
  deleteText: { color: '#e74c3c', fontSize: 13, fontWeight: '600' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', marginTop: 100 },
  emptyText: { fontSize: 16, color: '#888', marginBottom: 6 },
});
```

- [ ] **Step 2: Expo Go에서 기록 화면 확인**

- 홈에서 메뉴 결정 후 기록 탭 이동 → 항목 표시 확인
- 날짜 내림차순 정렬 확인
- 삭제 버튼 → Alert → 확인 시 항목 삭제 확인

- [ ] **Step 3: 커밋**

```bash
git add app/'(tabs)'/history.tsx
git commit -m "feat: 기록 화면 — 날짜별 먹은 메뉴 + 삭제"
```

---

## Task 14: 프로필 화면 (profile.tsx)

**Files:**
- Create: `app/(tabs)/profile.tsx`

- [ ] **Step 1: app/(tabs)/profile.tsx 작성**

```typescript
// app/(tabs)/profile.tsx
import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity,
  useColorScheme, SafeAreaView,
} from 'react-native';
import { useProfileStore, FamilyMember, AgeGroup } from '../../store/useProfileStore';
import { colors } from '../../constants/theme';

const AGE_GROUPS: AgeGroup[] = ['아이', '청소년', '어른', '노인'];

export default function ProfileScreen() {
  const isDark = useColorScheme() === 'dark';
  const { members, addMember, removeMember } = useProfileStore();

  const [name, setName] = useState('');
  const [ageGroup, setAgeGroup] = useState<AgeGroup>('어른');
  const [allergyInput, setAllergyInput] = useState('');

  const cardBg = isDark ? '#2d2d2d' : '#FFF';
  const textColor = isDark ? '#FFF' : colors.dark;

  function handleAdd() {
    const trimmed = name.trim();
    if (!trimmed) return;
    addMember({
      name: trimmed,
      ageGroup,
      allergies: allergyInput.split(',').map((s) => s.trim()).filter(Boolean),
      preferences: [],
    });
    setName('');
    setAllergyInput('');
    setAgeGroup('어른');
  }

  function renderMember(member: FamilyMember) {
    return (
      <View key={member.id} style={[styles.memberCard, { backgroundColor: cardBg }]}>
        <View style={styles.memberRow}>
          <Text style={[styles.memberName, { color: textColor }]}>
            {member.name} · {member.ageGroup}
          </Text>
          <TouchableOpacity onPress={() => removeMember(member.id)}>
            <Text style={styles.deleteText}>삭제</Text>
          </TouchableOpacity>
        </View>
        {member.allergies.length > 0 && (
          <Text style={styles.allergyText}>🚫 {member.allergies.join(', ')}</Text>
        )}
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: isDark ? colors.backgroundDark : '#F5F5F5' }]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={[styles.title, { color: textColor }]}>👨‍👩‍👧‍👦 가족 프로필</Text>

        <View style={[styles.form, { backgroundColor: cardBg }]}>
          <Text style={[styles.label, { color: textColor }]}>이름</Text>
          <TextInput
            style={[styles.input, { color: textColor }]}
            value={name}
            onChangeText={setName}
            placeholder="이름 입력"
            placeholderTextColor="#aaa"
          />

          <Text style={[styles.label, { color: textColor }]}>나이대</Text>
          <View style={styles.ageRow}>
            {AGE_GROUPS.map((ag) => (
              <TouchableOpacity
                key={ag}
                style={[styles.ageBtn, ageGroup === ag && styles.ageBtnActive]}
                onPress={() => setAgeGroup(ag)}
              >
                <Text style={[styles.ageBtnText, ageGroup === ag && styles.ageBtnActiveText]}>{ag}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={[styles.label, { color: textColor }]}>알레르기 (쉼표로 구분)</Text>
          <TextInput
            style={[styles.input, { color: textColor }]}
            value={allergyInput}
            onChangeText={setAllergyInput}
            placeholder="예: 견과류, 새우"
            placeholderTextColor="#aaa"
          />

          <TouchableOpacity style={styles.addBtn} onPress={handleAdd}>
            <Text style={styles.addBtnText}>구성원 추가</Text>
          </TouchableOpacity>
        </View>

        {members.length > 0 && (
          <>
            <Text style={[styles.subTitle, { color: textColor }]}>등록된 구성원 ({members.length}명)</Text>
            {members.map(renderMember)}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  scroll: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: '800', marginBottom: 16 },
  form: {
    borderRadius: 16, padding: 16, marginBottom: 20,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06, shadowRadius: 4, elevation: 2,
  },
  label: { fontSize: 14, fontWeight: '600', marginBottom: 8, marginTop: 12 },
  input: {
    borderWidth: 1.5, borderColor: colors.border, borderRadius: 12,
    paddingHorizontal: 14, paddingVertical: 12, fontSize: 15,
  },
  ageRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  ageBtn: {
    paddingVertical: 8, paddingHorizontal: 14, borderRadius: 20,
    borderWidth: 1.5, borderColor: colors.border, backgroundColor: '#FFF',
  },
  ageBtnActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  ageBtnText: { fontSize: 14, color: colors.dark },
  ageBtnActiveText: { color: '#FFF', fontWeight: '600' },
  addBtn: {
    backgroundColor: colors.primary, borderRadius: 12,
    paddingVertical: 14, alignItems: 'center', marginTop: 16,
  },
  addBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  subTitle: { fontSize: 16, fontWeight: '700', marginBottom: 12 },
  memberCard: {
    borderRadius: 14, padding: 14, marginBottom: 10,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
  },
  memberRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  memberName: { fontSize: 16, fontWeight: '600' },
  deleteText: { color: '#e74c3c', fontSize: 13, fontWeight: '600' },
  allergyText: { fontSize: 13, color: '#888', marginTop: 4 },
});
```

- [ ] **Step 2: Expo Go에서 프로필 화면 확인**

- 이름 입력 + 나이대 선택 + 알레르기 입력 → "구성원 추가" 클릭
- 구성원 카드 표시 + 알레르기 표시 확인
- 삭제 버튼으로 구성원 삭제 확인
- 홈 화면에서 추천 시 가족 정보 반영 확인 (Groq 프롬프트)

- [ ] **Step 3: 전체 테스트 실행**

```bash
npx jest --no-coverage
```

Expected: PASS (전체 스토어 + 컴포넌트 테스트)

- [ ] **Step 4: 최종 커밋**

```bash
git add app/'(tabs)'/profile.tsx
git commit -m "feat: 프로필 화면 — 가족 구성원 + 알레르기 설정"
git tag v0.1.0
```

---

## Self-Review 체크리스트

- [x] **스펙 커버리지**: 홈(조건4가지+추천+결정+다시추천) ✓, 냉장고(카테고리탭+빠른추가+직접입력+태그) ✓, 기록(날짜정렬+삭제) ✓, 프로필(구성원추가/삭제+알레르기) ✓
- [x] **이번 주 메뉴 중복 방지**: HistoryStore.getThisWeekMenus() → HomeScreen에서 recentMenus로 주입 ✓
- [x] **Groq JSON 파싱 실패 1회 재시도**: groq.ts Task 6 ✓
- [x] **AsyncStorage persist**: 3개 store 모두 적용 ✓
- [x] **타입 일관성**: MenuRecommendation, FamilyMember, HistoryEntry, AgeGroup — 모든 Task에서 동일 import 경로 사용 ✓
- [x] **Placeholder 없음**: 모든 Step에 완전한 코드 포함 ✓
