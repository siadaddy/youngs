#!/bin/bash
# ─────────────────────────────────────────────────────────────
# 시아아빠님의 AI 크리에이터 — 매일 07:00 KST 자동 실행
# crontab: 0 7 * * * /Users/youngchulyu/바이브코딩/ai-crew/run_daily.sh
# ─────────────────────────────────────────────────────────────

PYTHON=/opt/anaconda3/bin/python3
AI_CREW=/Users/youngchulyu/바이브코딩/ai-crew
NEWSLETTER=/Users/youngchulyu/바이브코딩/뉴스레터
LOG=$AI_CREW/crew.log

echo "" >> "$LOG"
echo "============================== $(date '+%Y-%m-%d %H:%M:%S') ==============================" >> "$LOG"

# ── Step 1: 뉴스레터 수집 (newsletter/.env 사용) ──
echo "[1/2] 뉴스레터 수집 시작..." >> "$LOG"
cd "$NEWSLETTER" && \
  "$PYTHON" newsletter_naver.py >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
  echo "  ⚠️  뉴스레터 수집 실패 (계속 진행)" >> "$LOG"
fi

# ── Step 2: AI 크리에이터 실행 ──
echo "[2/2] AI 크리에이터 실행..." >> "$LOG"
cd "$AI_CREW" && \
  NEWSLETTER_DIR="$NEWSLETTER" \
  "$PYTHON" main.py >> "$LOG" 2>&1

echo "============================== 완료 $(date '+%Y-%m-%d %H:%M:%S') ==============================" >> "$LOG"
