#!/bin/bash
# ─────────────────────────────────────────────────────────────
# 시아아빠님의 AI 크리에이터 — 매일 07:00 KST 자동 실행
# 뉴스 수집은 com.siadad.newsletter (06:40) 에서 별도 선행 실행
# ─────────────────────────────────────────────────────────────

PYTHON=/opt/anaconda3/bin/python3
AI_CREW=/Users/youngchulyu/vibe-coding/ai-crew
NEWSLETTER=/Users/youngchulyu/vibe-coding/newsletter
LOG=$AI_CREW/crew.log
TODAY=$(date '+%Y-%m-%d')

echo "" >> "$LOG"
echo "============================== $(date '+%Y-%m-%d %H:%M:%S') ==============================" >> "$LOG"

# ── 뉴스 데이터 확인 (06:40 수집이 완료됐는지) ──
DATA_FILE="$NEWSLETTER/${TODAY}_data.json"
if [ ! -f "$DATA_FILE" ]; then
  echo "  ⚠️  뉴스 데이터 없음 ($DATA_FILE) → 긴급 수집 시도..." >> "$LOG"
  cd "$NEWSLETTER" && "$PYTHON" newsletter_naver.py >> "$LOG" 2>&1
  if [ $? -ne 0 ]; then
    echo "  ⚠️  긴급 수집도 실패 — 뉴스 없이 진행" >> "$LOG"
  fi
else
  echo "  ✅ 뉴스 데이터 확인 완료 ($DATA_FILE)" >> "$LOG"
fi

# ── AI 크리에이터 실행 ──
echo "[실행] AI 크리에이터 시작..." >> "$LOG"
cd "$AI_CREW" && \
  NEWSLETTER_DIR="$NEWSLETTER" \
  "$PYTHON" main.py >> "$LOG" 2>&1

echo "============================== 완료 $(date '+%Y-%m-%d %H:%M:%S') ==============================" >> "$LOG"
