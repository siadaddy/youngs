# "오늘 저녁 뭐 먹지?" 앱 설계 문서

**작성일:** 2026-05-09  
**프로젝트 경로:** `/Users/youngchulyu/바이브코딩/dinner-tonight`  
**목표:** React Native + Expo 기반 AI 저녁 메뉴 추천 앱 (앱스토어/구글플레이 출시)

---

## 1. 기술 스택

| 항목 | 선택 |
|------|------|
| 프레임워크 | React Native + Expo (managed workflow) |
| 언어 | TypeScript |
| AI | Groq API (llama-3.3-70b-versatile) |
| 상태관리 | Zustand + persist 미들웨어 |
| 로컬저장 | AsyncStorage (Zustand persist 백엔드) |
| 네비게이션 | Expo Router (파일 기반 탭 라우팅) |

---

## 2. 폴더 구조

```
dinner-tonight/
├── app/
│   ├── (tabs)/
│   │   ├── index.tsx       # 홈 — 조건 선택 + AI 추천
│   │   ├── fridge.tsx      # 냉장고 — 식재료 관리
│   │   ├── history.tsx     # 기록 — 먹은 메뉴 히스토리
│   │   └── profile.tsx     # 프로필 — 가족 설정
│   └── _layout.tsx
├── components/
│   ├── ConditionPicker.tsx # 멀티셀렉트 조건 버튼 그룹
│   ├── MenuCard.tsx        # AI 추천 결과 카드 (로딩/에러 포함)
│   └── IngredientTag.tsx   # 식재료 태그 (X 버튼 포함)
├── store/
│   ├── useFridgeStore.ts   # 식재료 목록 (카테고리별)
│   ├── useProfileStore.ts  # 가족 구성원 + 알레르기
│   └── useHistoryStore.ts  # 날짜별 먹은 메뉴
├── lib/
│   └── groq.ts             # Groq API 단일 진입점
├── constants/
│   ├── ingredients.ts      # 자주 쓰는 식재료 목록 (카테고리별)
│   └── theme.ts            # 색상/폰트 상수
└── .env                    # EXPO_PUBLIC_GROQ_API_KEY
```

---

## 3. 데이터 모델

### FridgeStore
```typescript
interface FridgeStore {
  ingredients: string[];           // 현재 냉장고 식재료
  addIngredient: (name: string) => void;
  removeIngredient: (name: string) => void;
  clearAll: () => void;
}
```

### ProfileStore
```typescript
interface FamilyMember {
  id: string;
  name: string;
  ageGroup: '아이' | '청소년' | '어른' | '노인';
  allergies: string[];
  preferences: string[];   // 선호 음식 스타일
}

interface ProfileStore {
  members: FamilyMember[];
  addMember: (member: Omit<FamilyMember, 'id'>) => void;
  removeMember: (id: string) => void;
  updateMember: (id: string, updates: Partial<FamilyMember>) => void;
}
```

### HistoryStore
```typescript
interface HistoryEntry {
  id: string;
  date: string;            // YYYY-MM-DD
  menu: string;
  emoji: string;
}

interface HistoryStore {
  entries: HistoryEntry[];
  addEntry: (entry: Omit<HistoryEntry, 'id'>) => void;
  removeEntry: (id: string) => void;
  getThisWeekMenus: () => string[];   // 이번 주 메뉴명 목록
}
```

### Groq 응답 타입
```typescript
interface MenuRecommendation {
  menu: string;
  emoji: string;
  reason: string;
  recipe: [string, string, string];
  tip: string;
  alternatives: [string, string];
}
```

---

## 4. 데이터 흐름

```
냉장고 store ──┐
프로필 store ──┼──→ lib/groq.ts → Groq API → MenuRecommendation
기록 store ────┘         ↑
                  조건 선택 (홈 화면 로컬 state)
```

- 모든 store는 `zustand/middleware`의 `persist`로 AsyncStorage에 자동 저장
- `groq.ts`는 조건 + 재료 + 히스토리 + 프로필을 받아 프롬프트 조립 후 API 호출
- JSON 파싱 실패 시 1회 재시도, 그래도 실패하면 에러 throw

---

## 5. 화면별 설계

### 5-1. 홈 화면 (index.tsx)
- **조건 선택**: 4개 카테고리, 각 카테고리에서 1개 선택 (멀티셀렉트는 카테고리 내 단일 선택)
  - 스타일: 집밥 / 배달 / 외식
  - 기분: 가볍게 / 든든하게 / 특별하게
  - 인원: 혼자 / 둘이서 / 온 가족
  - 조리시간: 15분 이내 / 30분 / 여유있게
- **"추천받기" 버튼**: 조건 1개 이상 선택 시 활성화
- **MenuCard**: 로딩 중 스피너, 결과 표시, "이 메뉴로 결정!" / "다시 추천" 버튼

### 5-2. 냉장고 화면 (fridge.tsx)
- 카테고리 탭: 육류 / 채소 / 해산물 / 유제품 / 기타
- 자주 쓰는 식재료 빠른 추가 (탭 토글, `constants/ingredients.ts` 기반)
- 직접 입력 TextInput
- 등록된 식재료: `IngredientTag` 컴포넌트, X로 삭제

### 5-3. 기록 화면 (history.tsx)
- 날짜 내림차순 리스트
- 이번 주 먹은 항목은 AI 추천 시 프롬프트에서 제외
- 스와이프 삭제 (`react-native`의 `Swipeable` 또는 `PanResponder`)

### 5-4. 프로필 화면 (profile.tsx)
- 가족 구성원 추가/삭제
- 각 구성원: 이름, 나이대, 알레르기, 선호 스타일
- 저장된 프로필은 AI 프롬프트의 `[가족 정보]` 섹션에 주입

---

## 6. AI 프롬프트 설계

```typescript
// lib/groq.ts
systemPrompt = `당신은 한국 가정의 저녁 메뉴를 추천하는 전문가입니다.
반드시 JSON 형식으로만 응답하세요.`

userPrompt = `
오늘 저녁 메뉴를 추천해줘.

[조건]
- 스타일: ${conditions.style}
- 기분: ${conditions.mood}
- 인원: ${conditions.who}
- 조리시간: ${conditions.time}

[냉장고 재료]
${ingredients.join(', ')}

[이번 주 먹은 메뉴] (제외해줘)
${recentMenus.join(', ')}

[가족 정보]
${familyProfile}

JSON 형식으로만 응답:
{
  "menu": "메뉴명",
  "emoji": "이모지",
  "reason": "추천 이유 1문장",
  "recipe": ["1단계", "2단계", "3단계"],
  "tip": "꿀팁 1문장",
  "alternatives": ["대안메뉴1", "대안메뉴2"]
}`
```

---

## 7. 에러 처리

| 상황 | 처리 |
|------|------|
| Groq JSON 파싱 실패 | 1회 재시도 → 실패 시 "다시 시도해주세요" |
| API 키 미설정 | 개발 환경에서 콘솔 경고 |
| AsyncStorage 실패 | 무시, 메모리 상태만 유지 |
| 네트워크 오류 | 에러 메시지 표시 + 재시도 버튼 |

---

## 8. 디자인 시스템

```typescript
// constants/theme.ts
export const colors = {
  primary: '#FF6B35',    // 주황 — 메인 액션
  dark: '#2D3436',       // 다크 텍스트
  accent: '#FFEAA7',     // 연노랑 포인트
  background: '#FFFFFF', // 라이트 배경
  backgroundDark: '#1A1A2E', // 다크모드 배경
  surface: '#F8F9FA',
  border: '#E0E0E0',
};
```

- 카드형 UI, `borderRadius: 16`
- 시스템 폰트 (한글 최적화)
- 다크모드: `useColorScheme()` 훅 활용

---

## 9. 개발 순서

1. 프로젝트 세팅 + 폴더 구조 생성
2. Zustand store 3개 (fridge / profile / history) + AsyncStorage persist
3. Groq API 연동 (`lib/groq.ts`)
4. 홈 화면 UI + 추천 기능
5. 냉장고 화면
6. 기록 화면
7. 프로필 화면
8. 전체 연결 + 테스트

---

## 10. 환경 설정

```bash
npx create-expo-app@latest dinner-tonight --template blank-typescript
cd dinner-tonight
npx expo install expo-router zustand @react-native-async-storage/async-storage
```

`.env`:
```
EXPO_PUBLIC_GROQ_API_KEY=<groq_api_key>
```
