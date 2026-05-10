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
