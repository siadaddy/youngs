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
