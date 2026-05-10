#!/bin/bash
# ─────────────────────────────────────────────────────────────
# AI 코인 자동매매 — 15분마다 launchd로 실행 (매 시 :02/:17/:32/:47)
# stdout/stderr → plist StandardOutPath(trader.log) 로 자동 redirect
# ─────────────────────────────────────────────────────────────

PYTHON=/opt/anaconda3/bin/python3
TRADER=/Users/youngchulyu/vibe-coding/coin-trader

echo ""
echo "============================== $(date '+%Y-%m-%d %H:%M:%S') =============================="

# 네트워크 준비 대기 (절전 후 DNS 실패 방지)
for i in 1 2 3 4 5; do
  if nc -zw 3 api.bithumb.com 443 2>/dev/null; then
    break
  fi
  echo "  ⏳ 네트워크 대기 중... ($i/5)"
  sleep 5
done

cd "$TRADER" && "$PYTHON" main.py

echo "============================== 완료 $(date '+%Y-%m-%d %H:%M:%S') =============================="
