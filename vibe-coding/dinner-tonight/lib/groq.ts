const GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions';
const MODEL = 'llama-3.3-70b-versatile';

export interface RecommendationInput {
  conditions: { style: string; cuisine: string; mood: string; who: string; time: string; spicy: string };
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
  ingredients: string[];
  recipe: string[];
  tip: string;
  alternatives: [string, string];
}

function randomSeed() {
  const seeds = ['오늘은', '이번엔', '색다르게', '의외로', '특별히', '딱 오늘같은 날엔', '가끔은'];
  return seeds[Math.floor(Math.random() * seeds.length)];
}

const DISH_POOL: Record<string, string[]> = {
  '한식-찌개탕': ['김치찌개', '된장찌개', '순두부찌개', '부대찌개', '감자탕', '설렁탕', '곰탕', '갈비탕', '해장국', '황태국'],
  '한식-구이': ['삼겹살', '목살구이', '제육볶음', '불고기', '닭갈비', '갈비찜', '생선구이', '고등어구이', '삼치구이'],
  '한식-볶음면': ['비빔국수', '잡채', '떡볶이', '라볶이', '짜파게티', '쫄면', '비빔냉면', '물냉면', '막국수'],
  '한식-덮밥': ['오야코동', '규동', '돼지고기덮밥', '참치마요덮밥', '제육덮밥', '순두부덮밥', '쭈꾸미덮밥', '낙지덮밥'],
  '한식-전·튀김': ['파전', '김치전', '해물파전', '동그랑땡', '두부김치', '닭강정', '오징어튀김'],
  '중식': ['마파두부', '짜장면', '짬뽕', '탕수육', '깐풍기', '양장피', '팔보채', '동파육', '마라탕', '훠궈'],
  '일식': ['라멘', '돈카츠', '가츠동', '스시', '우동', '소바', '오코노미야키', '타코야키', '규카츠', '나베'],
  '양식': ['크림파스타', '토마토파스타', '봉골레파스타', '리조또', '스테이크', '함박스테이크', '피자', '샌드위치', '그라탱', '오믈렛'],
  '동남아': ['팟타이', '쌀국수', '분짜', '반미', '그린커리', '레드커리', '나시고렝', '쌀국수볶음', '코코넛밀크카레', '똠얌꿍'],
  '멕시칸': ['타코', '부리또', '퀘사디야', '나초', '치킨파히타', '과카몰리토스트'],
  '분식': ['떡볶이', '순대국', '김밥', '핫도그', '치즈볶이', '라면', '컵밥', '토스트'],
  '샐러드·가벼운': ['닭가슴살샐러드', '연어포케', '아보카도토스트', '그릭샐러드', '카프레제', '두부샐러드'],
  '디저트': ['티라미수', '크레이프', '와플', '팬케이크', '마카롱', '브라우니', '치즈케이크', '아이스크림파르페', '과일타르트', '크로플', '밀크티와 디저트', '초코퐁듀', '빙수', '호떡', '붕어빵'],
};

const CUISINE_CAT_MAP: Record<string, string[]> = {
  '한식': ['한식-찌개탕', '한식-구이', '한식-볶음면', '한식-덮밥', '한식-전·튀김'],
  '중식': ['중식'],
  '일식': ['일식'],
  '양식': ['양식'],
  '동남아': ['동남아'],
  '분식': ['분식'],
  '디저트': ['디저트'],
};

function pickDishSuggestion(recentMenus: string[], selectedCuisine?: string): { dish: string; avoidCategories: string } {
  const recentText = recentMenus.join(' ');

  let available = Object.entries(DISH_POOL);

  // 음식 종류 선택 시 해당 카테고리만 사용
  if (selectedCuisine && CUISINE_CAT_MAP[selectedCuisine]) {
    const targetCats = CUISINE_CAT_MAP[selectedCuisine];
    available = available.filter(([cat]) => targetCats.includes(cat));
  } else {
    // 선택 없으면 최근 메뉴와 겹치는 카테고리 제외
    available = available.filter(([cat]) => {
      if (cat.startsWith('한식') && (recentText.includes('찌개') || recentText.includes('불고기') || recentText.includes('삼겹'))) {
        return !cat.startsWith('한식-찌개') && !cat.startsWith('한식-구이');
      }
      return true;
    });
  }

  if (available.length === 0) available = Object.entries(DISH_POOL);

  const shuffled = [...available].sort(() => Math.random() - 0.5);
  const [, dishes] = shuffled[0];
  const dish = dishes[Math.floor(Math.random() * dishes.length)];

  const avoidList = recentMenus.length > 0
    ? `최근에 먹은 [${recentMenus.join(', ')}]과 같은 계열 음식은 절대 추천하지 마세요. 완전히 다른 나라 요리 또는 다른 조리 방식으로 추천하세요.`
    : '';

  return { dish, avoidCategories: avoidList };
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

  const { dish: suggestedDish, avoidCategories } = pickDishSuggestion(input.recentMenus, input.conditions.cuisine);
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
  "ingredients": ["재료1 (분량)", "재료2 (분량)", "재료3 (분량)"],
  "recipe": ["1단계: 구체적인 내용", "2단계: 구체적인 내용", "3단계: 구체적인 내용", "4단계: 구체적인 내용", "5단계: 마무리 및 플레이팅"],
  "tip": "더 맛있게 먹는 꿀팁 1문장",
  "alternatives": ["비슷한 느낌의 다른메뉴1", "전혀 다른 느낌의 다른메뉴2"]
}`
    : `${seed} 오늘 저녁 메뉴를 추천해줘.

[상황 조건]
- 식사 스타일: ${input.conditions.style || '무관'}
- 음식 종류: ${input.conditions.cuisine ? `반드시 ${input.conditions.cuisine} 요리로 추천할 것` : '제한 없음'}
- 현재 상황/기분: ${
  input.conditions.mood === '집에서 쉬고 싶어' ? '집에서 쉬고 싶은 날 — 편안하고 간단한 집밥, 배달 음식 위주로' :
  input.conditions.mood === '기분 전환하고 싶어' ? '우울하거나 지친 날 — 기분이 확 바뀔 수 있는 색다른 음식, 맛있어서 기분 좋아지는 메뉴, 위로가 되는 따뜻한 음식' :
  input.conditions.mood === '힘내고 싶어' ? '힘내야 하는 날 — 든든하고 영양가 있는 음식, 기운 나는 메뉴' :
  input.conditions.mood === '특별한 날이야' ? '기념일·특별한 날 — 평소엔 잘 안 먹는 특별한 메뉴, 레스토랑 분위기 나는 요리' :
  '무관'
}
- 먹는 인원: ${input.conditions.who || '무관'}
- 조리 가능 시간: ${input.conditions.time || '무관'}
- 맵기: ${input.conditions.spicy || '무관'}

[냉장고 보유 재료]
${input.ingredients.length > 0 ? input.ingredients.join(', ') : '특별히 없음 (뭐든 추천 가능)'}

[최근 먹은 메뉴 — 이 메뉴들과 같은 나라 요리, 같은 조리법, 비슷한 재료 모두 피할 것]
${input.recentMenus.length > 0 ? input.recentMenus.join(', ') : '없음'}
${avoidCategories}

[가족 구성 및 알레르기]
${input.familyProfile || '정보 없음'}

[오늘의 추천 후보 — 이 메뉴 또는 같은 계열에서 골라도 되고, 완전히 다른 선택도 환영]
"${suggestedDish}"

⚠️ 다양성 규칙:
- 김치찌개·된장찌개·삼겹살·불고기·라면처럼 흔하고 뻔한 메뉴는 최후 선택지로만 사용
- 최근 먹은 메뉴와 나라·조리법·재료가 하나라도 겹치면 절대 추천 금지
- 한식만 반복되면 반드시 다른 나라 요리로 전환할 것
- 구체적인 요리명으로 추천 (예: "파스타" X → "봉골레 파스타" O)

다음 JSON 형식으로만 응답해. emoji는 추천한 menu와 정확히 일치하는 음식 이모지 1개:
{
  "menu": "구체적인 메뉴명",
  "emoji": "이모지1개",
  "reason": "이 메뉴를 추천하는 이유 — 오늘 조건과 연결해서 1~2문장으로",
  "trendReason": "요즘 이 메뉴가 왜 인기인지 — SNS 화제·검색 급상승·계절 트렌드 등 실감나는 이유 한 문장",
${input.conditions.style === '배달' || input.conditions.style === '외식'
  ? `  "ingredients": [],
  "recipe": [],
  "tip": "주문 또는 방문 시 꿀팁 1문장",`
  : `  "ingredients": ["재료1 (분량)", "재료2 (분량)", "재료3 (분량)"],
  "recipe": ["1단계: 구체적인 내용", "2단계: 구체적인 내용", "3단계: 구체적인 내용", "4단계: 구체적인 내용", "5단계: 마무리 및 플레이팅"],
  "tip": "이 메뉴를 더 맛있게 먹는 꿀팁 1문장",`}
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
      temperature: 1.1,
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
