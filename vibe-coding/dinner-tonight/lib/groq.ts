const GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions';
const MODEL = 'llama-3.3-70b-versatile';

export interface RecommendationInput {
  conditions: { style: string; mood: string; who: string; time: string; spicy: string };
  ingredients: string[];
  recentMenus: string[];
  familyProfile: string;
  requestedMenu?: string;
}

export interface MenuRecommendation {
  menu: string;
  emoji: string;
  reason: string;
  trendReason: string;
  recipe: [string, string, string];
  tip: string;
  alternatives: [string, string];
}

function randomSeed() {
  const seeds = ['오늘은 특별히', '색다르게', '의외로', '가끔은', '이번엔'];
  return seeds[Math.floor(Math.random() * seeds.length)];
}

const CUISINE_TYPES = [
  '한식(찌개·볶음·구이·나물·면)',
  '중식(짜장·짬뽕·마파두부·탕수육)',
  '일식(라멘·돈카츠·오야코동·스시)',
  '양식(파스타·리조또·스테이크·샌드위치)',
  '분식(떡볶이·순대·김밥·라면)',
  '동남아식(팟타이·쌀국수·커리·볶음밥)',
  '멕시칸(타코·부리토·퀘사디야)',
  '한국식 퓨전(덮밥·비빔류·국밥)',
];

function pickCuisineHint(recentMenus: string[]): string {
  const shuffled = [...CUISINE_TYPES].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 2).join(' 또는 ');
}

function isKoreanEnough(text: string): boolean {
  if (!text || text.trim().length === 0) return true;
  const hangul = (text.match(/[가-힣ᄀ-ᇿ㄰-㆏]/g) ?? []).length;
  const meaningful = text.replace(/[\s\d.,!?()\-·…""'']/g, '').length;
  return meaningful === 0 || hangul / meaningful >= 0.4;
}

function hasNonKoreanScript(text: string): boolean {
  if (/[぀-ヿ]/.test(text)) return true;
  if (/[一-鿿㐀-䶿]/.test(text)) return true;
  if (/[À-ɏḀ-ỿ]/.test(text)) return true;
  if (/[؀-ۿ฀-๿]/.test(text)) return true;
  if (/[Ѐ-ӿ]/.test(text)) return true;
  return false;
}

function isResultKorean(result: MenuRecommendation): boolean {
  const fields = [result.menu, result.reason, result.tip, ...(result.recipe ?? []), ...(result.alternatives ?? [])];
  return fields.every((f) => !hasNonKoreanScript(f ?? '') && isKoreanEnough(f ?? ''));
}

async function callGroq(input: RecommendationInput): Promise<MenuRecommendation> {
  const apiKey = process.env.EXPO_PUBLIC_GROQ_API_KEY;
  if (!apiKey) throw new Error('API 키가 설정되지 않았습니다');

  const cuisineHint = pickCuisineHint(input.recentMenus);
  const seed = randomSeed();
  const isSpecificRequest = !!input.requestedMenu;

  const systemPrompt = `[CRITICAL LANGUAGE RULE] You MUST write ALL text fields in Korean (한국어/Hangul) ONLY. This is non-negotiable. No Japanese, Vietnamese, Chinese, Russian, English, or any other language is allowed anywhere in your response — not even a single word. Every character of every text field must be Korean Hangul or Korean punctuation. If you recommend a Japanese or Vietnamese dish, describe it entirely in Korean words.

당신은 15년 경력의 한국 가정식 전문 푸드 큐레이터입니다.
매번 창의적이고 다양한 메뉴를 추천하는 것이 당신의 핵심 역할입니다.

반드시 지켜야 할 원칙:
1. 모든 응답은 반드시 한국어(한글)로만 작성하세요.
2. 일본어(히라가나·가타카나), 베트남어, 영어, 중국어, 러시아어 등 외국어 표기를 절대 사용하지 마세요.
3. 메뉴명도 반드시 한국어로 표기하세요 (예: Ramen → 라멘, Pho → 쌀국수, カレー → 카레, Pasta → 파스타).
4. 조리법 각 단계도 한국어로만 작성하세요. 재료명·조리용어 모두 한국어 표기만 허용합니다.
5. 한식에만 치우치지 말고, 중식·일식·양식·분식·동남아식·멕시칸 등 폭넓게 추천하세요.
6. 최근 먹은 메뉴와 같은 '종류'도 피하세요.
7. 냉장고 재료를 활용할 수 있으면 좋지만, 재료가 없어도 훌륭한 메뉴를 추천하세요.
8. 레시피는 현실적이고 단계별로 명확하게 작성하세요.
9. 반드시 순수 JSON만 응답하세요. 마크다운 코드블록 없이.`;

  const userPrompt = isSpecificRequest
    ? `사용자가 "${input.requestedMenu}"를 먹고 싶다고 직접 선택했어. 이 메뉴에 대해 상세하게 알려줘.

[상황 조건]
- 식사 스타일: ${input.conditions.style || '무관'}
- 먹는 인원: ${input.conditions.who || '무관'}
- 조리 가능 시간: ${input.conditions.time || '무관'}
- 맵기: ${input.conditions.spicy || '무관'}

[가족 구성 및 알레르기]
${input.familyProfile || '정보 없음'}

menu는 반드시 "${input.requestedMenu}"로 고정 (한국어 표기). emoji는 이 음식과 정확히 일치하는 이모지 1개. 모든 텍스트는 한국어로만 작성. 다음 JSON으로 응답:
{
  "menu": "${input.requestedMenu}",
  "emoji": "이모지1개",
  "reason": "이 메뉴의 매력을 1~2문장으로",
  "trendReason": "요즘 이 메뉴가 왜 인기인지 — SNS 화제·검색 급상승·계절 트렌드 등 실감나는 이유 한 문장 (한국어만, 반드시 작성)",
  "recipe": ["재료 준비 및 첫 단계 (한국어만)", "핵심 조리 단계 (한국어만)", "마무리 및 플레이팅 (한국어만)"],
  "tip": "더 맛있게 먹는 꿀팁 1문장 (한국어만)",
  "alternatives": ["비슷한 느낌의 다른메뉴1", "전혀 다른 느낌의 다른메뉴2"]
}`
    : `${seed} 오늘 저녁 메뉴를 추천해줘.

[상황 조건]
- 식사 스타일: ${input.conditions.style || '무관'}
- 기분/입맛: ${input.conditions.mood || '무관'}
- 먹는 인원: ${input.conditions.who || '무관'}
- 조리 가능 시간: ${input.conditions.time || '무관'}
- 맵기: ${input.conditions.spicy || '무관'}

[냉장고 보유 재료]
${input.ingredients.length > 0 ? input.ingredients.join(', ') : '특별히 없음 (뭐든 추천 가능)'}

[이번 주 이미 먹은 메뉴 — 이것들과 비슷한 종류도 피해줘]
${input.recentMenus.length > 0 ? input.recentMenus.join(', ') : '없음 (자유롭게 추천)'}

[가족 구성 및 알레르기]
${input.familyProfile || '정보 없음'}

[추천 장르 힌트 — 오늘은 이쪽 방향으로 생각해봐]
${cuisineHint}

다음 JSON 형식으로만 응답해. emoji는 추천한 menu와 정확히 일치하는 음식 이모지 1개:
{
  "menu": "구체적인 메뉴명 (예: 크림 리조또, 마파두부 덮밥)",
  "emoji": "이모지1개",
  "reason": "이 메뉴를 추천하는 이유 — 오늘 조건과 연결해서 1~2문장으로",
  "trendReason": "요즘 이 메뉴가 왜 인기인지 — SNS 화제·검색 급상승·계절 트렌드·배달앱 인기 순위 등 실감나는 이유 한 문장 (한국어만, 반드시 작성)",
  "recipe": ["재료 준비 및 첫 단계 (한국어만)", "핵심 조리 단계 (한국어만)", "마무리 및 플레이팅 (한국어만)"],
  "tip": "이 메뉴를 더 맛있게 먹는 꿀팁 1문장 (한국어만)",
  "alternatives": ["비슷한 느낌의 대안메뉴1", "전혀 다른 느낌의 대안메뉴2"]
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
      temperature: 0.9,
    }),
  });

  if (!response.ok) {
    const errBody = await response.text().catch(() => '');
    throw new Error(`API 오류: ${response.status} ${errBody}`);
  }
  const data = await response.json();
  const raw: string = data.choices[0].message.content;
  const cleaned = raw.replace(/^```(?:json)?\n?/i, '').replace(/\n?```$/i, '').trim();
  return JSON.parse(cleaned) as MenuRecommendation;
}

export async function getMenuRecommendation(input: RecommendationInput): Promise<MenuRecommendation> {
  const MAX_ATTEMPTS = 3;
  let lastErr: any;
  let lastResult: MenuRecommendation | null = null;
  for (let i = 0; i < MAX_ATTEMPTS; i++) {
    try {
      const result = await callGroq(input);
      if (isResultKorean(result)) return result;
      lastResult = result;
    } catch (e: any) {
      if (e.message.includes('API 키')) throw e;
      lastErr = e;
    }
  }
  if (lastErr) throw new Error(lastErr.message ?? '메뉴 추천에 실패했습니다. 다시 시도해주세요.');
  if (lastResult) return lastResult;
  throw new Error('메뉴 추천에 실패했습니다. 다시 시도해주세요.');
}
