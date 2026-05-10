#!/bin/bash
# ─────────────────────────────────────────────────────────────
# 실시간 손절/익절 모니터 — 5분마다 launchd로 실행
# stdout/stderr → plist StandardOutPath(monitor.log) 로 자동 redirect
# ─────────────────────────────────────────────────────────────

PYTHON=/opt/anaconda3/bin/python3
TRADER=/Users/youngchulyu/vibe-coding/coin-trader

echo ""
echo "============================== $(date '+%Y-%m-%d %H:%M:%S') =============================="

cd "$TRADER" && "$PYTHON" price_monitor.py

echo "============================== 완료 $(date '+%Y-%m-%d %H:%M:%S') =============================="
