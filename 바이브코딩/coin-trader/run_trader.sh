#!/bin/bash
# ─────────────────────────────────────────────────────────────
# AI 코인 자동매매 — 4시간마다 launchd로 실행
# ─────────────────────────────────────────────────────────────

PYTHON=/opt/anaconda3/bin/python3
TRADER=/Users/youngchulyu/바이브코딩/coin-trader
LOG=$TRADER/trader.log

echo "" >> "$LOG"
echo "============================== $(date '+%Y-%m-%d %H:%M:%S') ==============================" >> "$LOG"

# 네트워크 준비 대기 (절전 후 깨어날 때 DNS 실패 방지)
for i in 1 2 3 4 5; do
  if ping -c 1 -t 3 api.upbit.com &>/dev/null; then
    break
  fi
  echo "  ⏳ 네트워크 대기 중... ($i/5)" >> "$LOG"
  sleep 5
done

cd "$TRADER" && "$PYTHON" main.py >> "$LOG" 2>&1

echo "============================== 완료 $(date '+%Y-%m-%d %H:%M:%S') ==============================" >> "$LOG"
