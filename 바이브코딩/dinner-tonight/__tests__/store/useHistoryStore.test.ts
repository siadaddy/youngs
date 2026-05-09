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
