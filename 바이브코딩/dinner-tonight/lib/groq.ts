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
