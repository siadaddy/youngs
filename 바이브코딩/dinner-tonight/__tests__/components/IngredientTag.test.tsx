import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { IngredientTag } from '../../components/IngredientTag';

describe('IngredientTag', () => {
  it('이름 렌더링', () => {
    const { getByText } = render(<IngredientTag name="양파" onRemove={() => {}} />);
    expect(getByText('양파')).toBeTruthy();
  });

  it('X 버튼 클릭 시 onRemove(name) 호출', () => {
    const onRemove = jest.fn();
    const { getByTestId } = render(<IngredientTag name="양파" onRemove={onRemove} />);
    fireEvent.press(getByTestId('remove-button'));
    expect(onRemove).toHaveBeenCalledWith('양파');
  });
});
