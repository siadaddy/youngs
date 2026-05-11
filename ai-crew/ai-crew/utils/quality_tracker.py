"""
📊 뉴스레터 품질 학습 트래커
━━━━━━━━━━━━━━━━━━━━━━━━
매일 실행 결과의 품질 이슈를 quality_log.json에 누적.
최근 7일간 자주 실패한 항목을 분석해 다음 날 프롬프트 힌트로 자동 주입.
"""

import os, json
from datetime import datetime, timedelta
from collections import Counter

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "quality_log.json")

# 이슈 타입 → 프롬프트 경고 문구
_ISSUE_HINTS = {
    "블랙리스트":    '⚠️ [학습경고] "와 이거 실화야", "레전드네", "대박이야" 등 블랙리스트 표현 — 최근 반복 실패 중. 절대 금지.',
    "제목-본문 불일치": "⚠️ [학습경고] 제목의 핵심 기업명·인물명·주제가 본문에 반드시 포함되어야 함 — 최근 반복 실패 중.",
    "해시태그":      "⚠️ [학습경고] 해시태그 8개 이상 필수, 본문 끝 한 줄로 — 최근 반복 실패 중.",
    "품질 오류":     "⚠️ [학습경고] 깨진 자모·한자·외국어·격식체(습니다/됩니다) — 최근 반복 실패 중.",
    "도입부 유사":   "⚠️ [학습경고] 카드마다 완전히 다른 도입부 — 같은 패턴 반복이 최근 자주 발생. 첫 문장 각도를 완전히 다르게.",
    "반복 문장":     "⚠️ [학습경고] 반복 문장 금지 — 최근 자주 발생. 각 문장은 새로운 정보를 담아야 함.",
}


def load_log() -> dict:
    if not os.path.exists(LOG_FILE):
        return {"runs": [], "updated": ""}
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"runs": [], "updated": ""}


def _save_log(data: dict):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_run(date: str, entries: list):
    """
    매일 실행 후 품질 결과 저장.
    entries: [(label, retry_count, issues_list), ...]
    """
    data = load_log()

    cards, all_issues = [], []
    total_retries = 0

    for label, retries, issues in entries:
        cards.append({
            "label":   label,
            "passed":  len(issues) == 0,
            "retries": retries,
            "issues":  issues,
        })
        total_retries += retries
        all_issues.extend(issues)

    passed_count = sum(1 for c in cards if c["passed"])
    pass_rate = round(passed_count / len(cards), 2) if cards else 1.0

    run_entry = {
        "date":          date,
        "cards":         cards,
        "total_retries": total_retries,
        "pass_rate":     pass_rate,
        "issue_summary": all_issues,
    }

    runs = [r for r in data.get("runs", []) if r["date"] != date]
    runs.insert(0, run_entry)
    data["runs"]    = runs[:30]   # 최대 30일
    data["updated"] = date
    _save_log(data)

    print(f"  📚 품질 학습 기록: {date} | 통과율 {pass_rate:.0%} | 재생성 {total_retries}회")
    if all_issues:
        cnt = Counter(_normalize(i) for i in all_issues if _normalize(i))
        top = ", ".join(f"{k}({v}회)" for k, v in cnt.most_common(3))
        print(f"     이슈 분포: {top}")


def get_adaptive_hints(days: int = 7) -> str:
    """
    최근 N일간 2회 이상 발생한 이슈 → 프롬프트 경고 문구 반환.
    이슈 없으면 빈 문자열.
    """
    data = load_log()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [r for r in data.get("runs", []) if r.get("date", "") >= cutoff]

    if not recent:
        return ""

    counter = Counter()
    for run in recent:
        for issue in run.get("issue_summary", []):
            t = _normalize(issue)
            if t:
                counter[t] += 1

    freq = [(t, c) for t, c in counter.most_common() if c >= 2]
    if not freq:
        return ""

    lines = [f"\n\n📚 학습 힌트 (최근 {days}일 반복 실패 항목 — 특별 주의):"]
    for issue_type, cnt in freq:
        hint = _ISSUE_HINTS.get(issue_type)
        if hint:
            lines.append(f"{hint} ({cnt}회 발생)")

    return "\n".join(lines) if len(lines) > 1 else ""


def get_summary(days: int = 30) -> list:
    """품질 통계 요약 출력용"""
    data = load_log()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [r for r in data.get("runs", []) if r.get("date", "") >= cutoff]

    if not recent:
        return [f"📊 품질 로그 없음 (최근 {days}일)"]

    counter = Counter()
    total_retries = 0
    pass_rates = []

    for run in recent:
        total_retries += run.get("total_retries", 0)
        pass_rates.append(run.get("pass_rate", 1.0))
        for issue in run.get("issue_summary", []):
            t = _normalize(issue)
            if t:
                counter[t] += 1

    avg = sum(pass_rates) / len(pass_rates)
    lines = [
        f"📊 뉴스레터 품질 통계 (최근 {days}일 / {len(recent)}회 실행)",
        f"  평균 통과율 : {avg:.0%}",
        f"  총 재생성   : {total_retries}회",
    ]
    if counter:
        lines.append("  이슈 빈도:")
        for t, c in counter.most_common():
            lines.append(f"    {t}: {c}회")
    return lines


def _normalize(issue: str) -> str:
    """이슈 문자열 → 타입 키워드"""
    if "블랙리스트" in issue:
        return "블랙리스트"
    if "제목-본문" in issue or "불일치" in issue:
        return "제목-본문 불일치"
    if "해시태그" in issue:
        return "해시태그"
    if "품질 오류" in issue:
        return "품질 오류"
    if "도입부" in issue:
        return "도입부 유사"
    if "반복 문장" in issue:
        return "반복 문장"
    return ""
