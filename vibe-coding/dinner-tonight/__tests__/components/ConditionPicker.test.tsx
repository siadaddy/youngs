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
