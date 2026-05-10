export const INGREDIENT_CATEGORIES = ['육류', '채소', '해산물', '유제품', '기타'] as const;
export type IngredientCategory = typeof INGREDIENT_CATEGORIES[number];

export const COMMON_INGREDIENTS: Record<IngredientCategory, string[]> = {
  육류: ['소고기', '돼지고기', '닭고기', '삼겹살', '다진고기', '소세지', '베이컨'],
  채소: ['양파', '마늘', '대파', '감자', '당근', '시금치', '깻잎', '고추', '애호박', '버섯'],
  해산물: ['새우', '오징어', '조개', '고등어', '참치캔', '멸치', '게맛살'],
  유제품: ['달걀', '우유', '치즈', '버터', '요거트'],
  기타: ['두부', '김치', '라면', '쌀', '된장', '간장', '고추장', '참기름', '들기름'],
};
