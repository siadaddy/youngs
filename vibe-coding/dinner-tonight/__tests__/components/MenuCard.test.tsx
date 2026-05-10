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

  it('추천 결과 — 메뉴명·이유·레시피 렌더링', () => {
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
