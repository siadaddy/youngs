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
