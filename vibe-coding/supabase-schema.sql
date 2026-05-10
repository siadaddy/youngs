CREATE TABLE IF NOT EXISTS news_cards (
  id          bigserial PRIMARY KEY,
  date        date        NOT NULL,
  title       text        NOT NULL,
  summary     text,
  image_url   text,
  category    text,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX idx_news_cards_date ON news_cards(date);

-- RLS 비활성화 (추후 설정)
ALTER TABLE news_cards DISABLE ROW LEVEL SECURITY;
