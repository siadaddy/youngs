#!/bin/bash
# ─────────────────────────────────────────────────────────────
# AI 코인 자동매매 — 1시간마다 launchd로 실행
# stdout/stderr → plist StandardOutPath(trader.log) 로 자동 redirect
# ─────────────────────────────────────────────────────────────

PYTHON=/opt/anaconda3/bin/python3
TRADER=/Users/youngchulyu/바이브코딩/coin-trader

echo ""
echo "============================== $(date '+%Y-%m-%d %H:%M:%S') =============================="

# 네트워크 준비 대기 (절전 후 DNS 실패 방지)
# macOS: nc -zw 로 포트 연결 테스트 (ping -t 는 TTL 옵션이라 timeout 미지원)
for i in 1 2 3 4 5; do
  if nc -zw 3 api.upbit.com 443 2>/dev/null; then
    break
  fi
  echo "  ⏳ 네트워크 대기 중... ($i/5)"
  sleep 5
done

cd "$TRADER" && "$PYTHON" main.py

echo "============================== 완료 $(date '+%Y-%m-%d %H:%M:%S') =============================="
