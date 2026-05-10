const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.title = 'BMW 서비스센터 월간 지점장 회의';
pres.author = '시아 아빠';

// ── 색상 팔레트 ──────────────────────────────────────────
const C = {
  bmwBlue:   "1C69D4",
  bmwBlueLt: "4D90F0",
  darkBg:    "080C14",
  navyBg:    "0F1520",
  cardBg:    "141C2E",
  white:     "FFFFFF",
  offWhite:  "F1F5F9",
  slate:     "64748B",
  slate2:    "94A3B8",
  green:     "10B981",
  red:       "EF4444",
  gold:      "F59E0B",
  purple:    "A78BFA",
  border:    "1E2D4A",
};

const makeShadow = () => ({ type: "outer", blur: 8, offset: 3, angle: 135, color: "000000", opacity: 0.3 });

// ══════════════════════════════════════════════════════════
// 슬라이드 1: 표지
// ══════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: C.darkBg };

  // 왼쪽 BMW 블루 사이드바
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 5.625,
    fill: { color: C.bmwBlue }, line: { color: C.bmwBlue }
  });

  // 오른쪽 장식 박스
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 7.6, y: 0, w: 2.4, h: 5.625,
    fill: { color: "0D1526" }, line: { color: "0D1526" }
  });
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 7.6, y: 0, w: 0.06, h: 5.625,
    fill: { color: C.bmwBlue }, line: { color: C.bmwBlue }
  });

  // BMW 로고 텍스트 (우측 상단)
  sl.addShape(pres.shapes.OVAL, {
    x: 8.1, y: 0.35, w: 1.5, h: 1.5,
    fill: { color: C.bmwBlue }, line: { color: C.white, pt: 3 }
  });
  sl.addText("BMW", {
    x: 8.1, y: 0.75, w: 1.5, h: 0.7,
    fontSize: 18, bold: true, color: C.white, align: "center",
    fontFace: "Arial Black", margin: 0
  });

  // 서브타이틀 레이블
  sl.addText("SERVICE CENTER", {
    x: 0.45, y: 0.5, w: 6.5, h: 0.4,
    fontSize: 11, bold: true, color: C.bmwBlueLt,
    charSpacing: 5, fontFace: "Arial", margin: 0
  });

  // 메인 타이틀
  sl.addText("월간 지점장 회의", {
    x: 0.45, y: 1.05, w: 7.0, h: 1.1,
    fontSize: 46, bold: true, color: C.white,
    fontFace: "Arial Black", margin: 0
  });

  // 구분선
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: 2.25, w: 5.5, h: 0.05,
    fill: { color: C.bmwBlue }, line: { color: C.bmwBlue }
  });

  // 지점명 입력 영역
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: 2.55, w: 3.8, h: 0.62,
    fill: { color: "0D1526" }, line: { color: C.border, pt: 1 }
  });
  sl.addText("[ 지점명 입력 ]", {
    x: 0.45, y: 2.55, w: 3.8, h: 0.62,
    fontSize: 15, color: C.slate, align: "center", valign: "middle",
    fontFace: "Arial", margin: 0
  });

  // 날짜 입력 영역
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 4.4, y: 2.55, w: 2.8, h: 0.62,
    fill: { color: "0D1526" }, line: { color: C.border, pt: 1 }
  });
  sl.addText("[ 날짜 입력 ]", {
    x: 4.4, y: 2.55, w: 2.8, h: 0.62,
    fontSize: 15, color: C.slate, align: "center", valign: "middle",
    fontFace: "Arial", margin: 0
  });

  // 하단 정보
  sl.addText("작성자: _______________   확인: _______________   승인: _______________", {
    x: 0.45, y: 4.95, w: 7.0, h: 0.35,
    fontSize: 10, color: C.slate, fontFace: "Calibri", margin: 0
  });

  // 우측 하단 연도
  sl.addText("2026", {
    x: 7.7, y: 4.5, w: 2.1, h: 0.7,
    fontSize: 28, bold: true, color: C.border, align: "center",
    fontFace: "Arial Black", margin: 0
  });
}

// ══════════════════════════════════════════════════════════
// 슬라이드 2: 이달의 핵심 KPI
// ══════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: C.navyBg };

  // 상단 헤더 바
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75,
    fill: { color: "0A0E18" }, line: { color: "0A0E18" }
  });
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 0.75,
    fill: { color: C.bmwBlue }, line: { color: C.bmwBlue }
  });
  sl.addText("이달의 핵심 KPI", {
    x: 0.38, y: 0, w: 7, h: 0.75,
    fontSize: 18, bold: true, color: C.white,
    fontFace: "Arial Black", valign: "middle", margin: 0
  });
  sl.addText("기준: 당월 1일 ~ 말일", {
    x: 7.5, y: 0, w: 2.3, h: 0.75,
    fontSize: 10, color: C.slate2, align: "right", valign: "middle",
    fontFace: "Calibri", margin: 0
  });

  // KPI 카드 4개
  const cards = [
    { label: "월간 입고 대수", value: "284", unit: "대", target: "목표 320대", rate: "+8%", rateUp: true, color: C.bmwBlue, barColor: C.bmwBlue, x: 0.22 },
    { label: "서비스 매출",    value: "4.2", unit: "억", target: "목표 4.8억", rate: "+12%", rateUp: true, color: C.green,   barColor: C.green,   x: 2.70 },
    { label: "고객만족도 CSI", value: "92.4", unit: "점", target: "목표 90점+", rate: "목표초과", rateUp: true, color: C.gold,    barColor: C.gold,    x: 5.18 },
    { label: "부품 매출",      value: "1.1",  unit: "억", target: "목표 1.3억", rate: "-3%",  rateUp: false, color: C.purple,  barColor: C.purple,  x: 7.66 },
  ];

  cards.forEach(card => {
    const cy = 0.95;
    const cw = 2.25;
    const ch = 4.4;

    // 카드 배경
    sl.addShape(pres.shapes.RECTANGLE, {
      x: card.x, y: cy, w: cw, h: ch,
      fill: { color: C.cardBg }, line: { color: C.border, pt: 1 },
      shadow: makeShadow()
    });
    // 하단 컬러 바
    sl.addShape(pres.shapes.RECTANGLE, {
      x: card.x, y: cy + ch - 0.07, w: cw, h: 0.07,
      fill: { color: card.barColor }, line: { color: card.barColor }
    });

    // 레이블
    sl.addText(card.label, {
      x: card.x + 0.18, y: cy + 0.22, w: cw - 0.36, h: 0.38,
      fontSize: 10, bold: true, color: C.slate2,
      charSpacing: 1, fontFace: "Arial", margin: 0
    });

    // 수치
    sl.addText([
      { text: card.value, options: { fontSize: 42, bold: true, color: card.color, fontFace: "Arial Black" } },
      { text: " " + card.unit, options: { fontSize: 18, bold: true, color: card.color, fontFace: "Arial" } }
    ], {
      x: card.x + 0.12, y: cy + 0.72, w: cw - 0.24, h: 1.0,
      valign: "middle", margin: 0
    });

    // 목표
    sl.addText(card.target, {
      x: card.x + 0.18, y: cy + 1.8, w: cw - 0.36, h: 0.35,
      fontSize: 10, color: C.slate, fontFace: "Calibri", margin: 0
    });

    // 진행률 바 배경
    sl.addShape(pres.shapes.RECTANGLE, {
      x: card.x + 0.18, y: cy + 2.28, w: cw - 0.36, h: 0.12,
      fill: { color: "1E2D4A" }, line: { color: "1E2D4A" }
    });
    // 진행률 바 채움 (약 87%)
    sl.addShape(pres.shapes.RECTANGLE, {
      x: card.x + 0.18, y: cy + 2.28, w: (cw - 0.36) * 0.87, h: 0.12,
      fill: { color: card.barColor }, line: { color: card.barColor }
    });

    // 전월 대비
    const rateColor = card.rateUp ? C.green : C.red;
    const rateBg    = card.rateUp ? "0D2E1F" : "2E0D0D";
    sl.addShape(pres.shapes.RECTANGLE, {
      x: card.x + 0.18, y: cy + 2.65, w: cw - 0.36, h: 0.45,
      fill: { color: rateBg }, line: { color: rateBg }
    });
    sl.addText((card.rateUp ? "▲ " : "▼ ") + "전월 대비 " + card.rate, {
      x: card.x + 0.18, y: cy + 2.65, w: cw - 0.36, h: 0.45,
      fontSize: 10, bold: true, color: rateColor,
      align: "center", valign: "middle", fontFace: "Arial", margin: 0
    });

    // 입력란 안내
    sl.addText("실적 입력:", {
      x: card.x + 0.18, y: cy + 3.35, w: cw - 0.36, h: 0.25,
      fontSize: 9, color: C.slate, fontFace: "Calibri", margin: 0
    });
    sl.addShape(pres.shapes.RECTANGLE, {
      x: card.x + 0.18, y: cy + 3.62, w: cw - 0.36, h: 0.45,
      fill: { color: "0A0E18" }, line: { color: C.border, pt: 1 }
    });
  });
}

// ══════════════════════════════════════════════════════════
// 슬라이드 3: 실적 상세 비교
// ══════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: C.navyBg };

  // 헤더
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75,
    fill: { color: "0A0E18" }, line: { color: "0A0E18" }
  });
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 0.75,
    fill: { color: C.bmwBlue }, line: { color: C.bmwBlue }
  });
  sl.addText("실적 상세 비교", {
    x: 0.38, y: 0, w: 7, h: 0.75,
    fontSize: 18, bold: true, color: C.white,
    fontFace: "Arial Black", valign: "middle", margin: 0
  });

  // 테이블 헤더 행
  const cols = ["항목", "전월", "금월", "목표", "달성률", "전월 대비"];
  const colW = [2.2, 1.3, 1.3, 1.3, 1.3, 1.55];
  const tableX = 0.5;
  const rowH = 0.52;

  // 헤더 배경
  sl.addShape(pres.shapes.RECTANGLE, {
    x: tableX, y: 0.9, w: 9.0, h: rowH,
    fill: { color: C.bmwBlue }, line: { color: C.bmwBlue }
  });
  let cx = tableX;
  cols.forEach((col, i) => {
    sl.addText(col, {
      x: cx, y: 0.9, w: colW[i], h: rowH,
      fontSize: 11, bold: true, color: C.white,
      align: i === 0 ? "left" : "center", valign: "middle",
      fontFace: "Arial", margin: [0, 0, 0, i === 0 ? 10 : 0]
    });
    cx += colW[i];
  });

  // 데이터 행
  const rows = [
    ["입고 대수",     "263대",  "284대",  "320대",  "88%",  "▲ +8%"],
    ["서비스 매출",   "3.7억",  "4.2억",  "4.8억",  "87%",  "▲ +12%"],
    ["고객만족도 CSI","90.1점", "92.4점", "90.0점", "102%", "▲ +2.3p"],
    ["부품 매출",     "1.1억",  "1.1억",  "1.3억",  "83%",  "▼ -3%"],
    ["재방문율",      "64%",    "71%",    "70%",    "101%", "▲ +7%p"],
    ["평균 수리기간", "2.8일",  "2.4일",  "2.5일",  "달성", "▲ 개선"],
    ["SA 1인당 생산성","—",     "—",      "—",      "—",    "직접 입력"],
  ];

  rows.forEach((row, ri) => {
    const ry = 0.9 + rowH + ri * rowH;
    const rowBg = ri % 2 === 0 ? C.cardBg : "111827";
    sl.addShape(pres.shapes.RECTANGLE, {
      x: tableX, y: ry, w: 9.0, h: rowH,
      fill: { color: rowBg }, line: { color: rowBg }
    });

    let cx2 = tableX;
    row.forEach((cell, ci) => {
      let color = C.offWhite;
      if (ci === 4) { // 달성률
        if (cell === "달성" || parseInt(cell) >= 100) color = C.green;
        else if (parseInt(cell) < 85) color = C.red;
        else color = C.gold;
      }
      if (ci === 5) { // 전월 대비
        color = cell.startsWith("▲") ? C.green : cell.startsWith("▼") ? C.red : C.slate2;
      }
      sl.addText(cell, {
        x: cx2, y: ry, w: colW[ci], h: rowH,
        fontSize: 11, color: color, bold: ci === 0 || ci >= 4,
        align: ci === 0 ? "left" : "center", valign: "middle",
        fontFace: "Calibri", margin: [0, 0, 0, ci === 0 ? 10 : 0]
      });
      cx2 += colW[ci];
    });

    // 하단 구분선
    sl.addShape(pres.shapes.LINE, {
      x: tableX, y: ry + rowH, w: 9.0, h: 0,
      line: { color: "1E2D4A", pt: 0.5 }
    });
  });

  // 범례
  sl.addText("■ 초과달성(100%+)   ■ 부분달성(85-99%)   ■ 미달(85% 미만)", {
    x: 0.5, y: 5.15, w: 9, h: 0.35,
    fontSize: 9, color: C.slate, align: "right",
    fontFace: "Calibri", margin: 0
  });
}

// ══════════════════════════════════════════════════════════
// 슬라이드 4: 주요 안건
// ══════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: C.navyBg };

  // 헤더
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75,
    fill: { color: "0A0E18" }, line: { color: "0A0E18" }
  });
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 0.75,
    fill: { color: C.bmwBlue }, line: { color: C.bmwBlue }
  });
  sl.addText("주요 안건", {
    x: 0.38, y: 0, w: 7, h: 0.75,
    fontSize: 18, bold: true, color: C.white,
    fontFace: "Arial Black", valign: "middle", margin: 0
  });
  sl.addText("총 소요시간: 90분", {
    x: 7.5, y: 0, w: 2.3, h: 0.75,
    fontSize: 10, color: C.slate2, align: "right", valign: "middle",
    fontFace: "Calibri", margin: 0
  });

  const agendas = [
    { num: "01", title: "전월 실적 검토 및 피드백",   desc: "KPI 달성 현황 공유 · 미달 항목 원인 분석 · 담당자 코멘트",    time: "10:00 – 10:20" },
    { num: "02", title: "부품 매출 부진 원인 분석",   desc: "재고 현황 점검 · 수요 예측 검토 · 개선 방안 논의",           time: "10:20 – 10:40" },
    { num: "03", title: "고객 컴플레인 케이스 리뷰",  desc: "이달 VOC 주요 사례 공유 · 재발 방지 대책 수립",              time: "10:40 – 11:00" },
    { num: "04", title: "다음달 목표 및 캠페인 계획", desc: "5월 시즌점검 캠페인 · 인력 운영 · 예산 계획",               time: "11:00 – 11:20" },
    { num: "05", title: "자유 안건 및 Q&A",           desc: "현장 건의사항 · 본사 전달사항 · 기타 공유",                  time: "11:20 – 11:30" },
  ];

  agendas.forEach((ag, i) => {
    const ay = 0.92 + i * 0.9;
    const ah = 0.82;

    // 카드 배경
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.3, y: ay, w: 9.4, h: ah,
      fill: { color: C.cardBg }, line: { color: C.border, pt: 1 }
    });
    // 번호 박스
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.3, y: ay, w: 0.7, h: ah,
      fill: { color: C.bmwBlue }, line: { color: C.bmwBlue }
    });
    sl.addText(ag.num, {
      x: 0.3, y: ay, w: 0.7, h: ah,
      fontSize: 14, bold: true, color: C.white,
      align: "center", valign: "middle",
      fontFace: "Arial Black", margin: 0
    });

    // 타이틀
    sl.addText(ag.title, {
      x: 1.15, y: ay + 0.06, w: 6.2, h: 0.36,
      fontSize: 13, bold: true, color: C.white,
      fontFace: "Arial", valign: "middle", margin: 0
    });
    // 설명
    sl.addText(ag.desc, {
      x: 1.15, y: ay + 0.44, w: 6.2, h: 0.3,
      fontSize: 9.5, color: C.slate2,
      fontFace: "Calibri", valign: "middle", margin: 0
    });

    // 시간 배지
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 7.6, y: ay + 0.18, w: 1.85, h: 0.44,
      fill: { color: "0D1526" }, line: { color: C.border, pt: 1 }
    });
    sl.addText(ag.time, {
      x: 7.6, y: ay + 0.18, w: 1.85, h: 0.44,
      fontSize: 10, bold: true, color: C.bmwBlueLt,
      align: "center", valign: "middle",
      fontFace: "Calibri", margin: 0
    });
  });
}

// ══════════════════════════════════════════════════════════
// 슬라이드 5: 액션 아이템
// ══════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: C.navyBg };

  // 헤더
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75,
    fill: { color: "0A0E18" }, line: { color: "0A0E18" }
  });
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 0.75,
    fill: { color: C.bmwBlue }, line: { color: C.bmwBlue }
  });
  sl.addText("액션 아이템", {
    x: 0.38, y: 0, w: 5, h: 0.75,
    fontSize: 18, bold: true, color: C.white,
    fontFace: "Arial Black", valign: "middle", margin: 0
  });

  // 컬럼 헤더
  const colLabels = ["상태", "액션 내용", "담당자", "기한", "비고"];
  const colWidths = [0.7, 4.5, 1.5, 1.5, 1.5];
  const tableX = 0.3;

  sl.addShape(pres.shapes.RECTANGLE, {
    x: tableX, y: 0.88, w: 9.4, h: 0.44,
    fill: { color: "0D1526" }, line: { color: C.border }
  });
  let hx = tableX;
  colLabels.forEach((lbl, i) => {
    sl.addText(lbl, {
      x: hx + 0.08, y: 0.88, w: colWidths[i] - 0.08, h: 0.44,
      fontSize: 10, bold: true, color: C.bmwBlueLt,
      charSpacing: 1, valign: "middle", fontFace: "Arial", margin: 0
    });
    hx += colWidths[i];
  });

  const items = [
    { done: true,  action: "SA 응대 매뉴얼 업데이트",      owner: "서비스팀",  due: "완료",      note: "" },
    { done: true,  action: "전월 VOC 결과 분석 보고",       owner: "품질팀",    due: "완료",      note: "" },
    { done: false, action: "부품 재고 최적화 방안 제출",    owner: "부품팀",    due: "5/2(금)",   note: "최우선" },
    { done: false, action: "신규 SA 교육 일정 확정",        owner: "인사팀",    due: "5/9(금)",   note: "" },
    { done: false, action: "5월 시즌점검 프로모션 기획",    owner: "마케팅",    due: "5/16(금)",  note: "" },
    { done: false, action: "본사 품질 감사 사전 점검",      owner: "지점장",    due: "5/20(수)",  note: "중요" },
    { done: false, action: "신규 안건 입력란",              owner: "___",       due: "___",       note: "___" },
  ];

  items.forEach((item, i) => {
    const ry = 1.32 + i * 0.6;
    const rh = 0.52;
    const rowBg = i % 2 === 0 ? C.cardBg : "111827";

    sl.addShape(pres.shapes.RECTANGLE, {
      x: tableX, y: ry, w: 9.4, h: rh,
      fill: { color: rowBg }, line: { color: "1E2D4A", pt: 0.5 }
    });

    // 체크박스
    const checkColor = item.done ? C.green : (i === items.length - 1 ? C.border : C.gold);
    sl.addShape(pres.shapes.RECTANGLE, {
      x: tableX + 0.12, y: ry + 0.12, w: 0.28, h: 0.28,
      fill: { color: item.done ? "0D2E1F" : "1E2D4A" },
      line: { color: checkColor, pt: 1.5 }
    });
    if (item.done) {
      sl.addText("✓", {
        x: tableX + 0.12, y: ry + 0.12, w: 0.28, h: 0.28,
        fontSize: 10, bold: true, color: C.green,
        align: "center", valign: "middle", margin: 0
      });
    }

    // 액션 내용
    const textColor = item.done ? C.slate : C.white;
    sl.addText(item.action, {
      x: tableX + 0.75, y: ry, w: 4.45, h: rh,
      fontSize: 11, color: textColor, bold: !item.done && i !== items.length - 1,
      valign: "middle", fontFace: "Calibri",
      strike: item.done, margin: 0
    });

    // 담당자
    sl.addText(item.owner, {
      x: tableX + 5.25, y: ry, w: 1.4, h: rh,
      fontSize: 10, color: item.done ? C.slate : C.bmwBlueLt,
      align: "center", valign: "middle", fontFace: "Calibri", margin: 0
    });

    // 기한
    sl.addText(item.due, {
      x: tableX + 6.7, y: ry, w: 1.4, h: rh,
      fontSize: 10, color: item.done ? C.slate : C.gold,
      align: "center", valign: "middle", fontFace: "Calibri", margin: 0
    });

    // 비고
    const noteColor = item.note === "최우선" ? C.red : item.note === "중요" ? C.gold : C.slate;
    sl.addText(item.note, {
      x: tableX + 8.1, y: ry, w: 1.4, h: rh,
      fontSize: 10, color: noteColor, bold: item.note !== "" && item.note !== "___",
      align: "center", valign: "middle", fontFace: "Calibri", margin: 0
    });
  });
}

// ══════════════════════════════════════════════════════════
// 슬라이드 6: 다음달 목표 + 특이사항
// ══════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: C.navyBg };

  // 헤더
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75,
    fill: { color: "0A0E18" }, line: { color: "0A0E18" }
  });
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 0.75,
    fill: { color: C.bmwBlue }, line: { color: C.bmwBlue }
  });
  sl.addText("다음달 목표 및 특이사항", {
    x: 0.38, y: 0, w: 8, h: 0.75,
    fontSize: 18, bold: true, color: C.white,
    fontFace: "Arial Black", valign: "middle", margin: 0
  });

  // ── 왼쪽: 다음달 목표 ──
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 0.92, w: 4.5, h: 0.42,
    fill: { color: "0D1526" }, line: { color: C.border }
  });
  sl.addText("다음달 목표", {
    x: 0.3, y: 0.92, w: 4.5, h: 0.42,
    fontSize: 11, bold: true, color: C.bmwBlueLt,
    charSpacing: 2, align: "center", valign: "middle",
    fontFace: "Arial", margin: 0
  });

  const goals = [
    { label: "입고 대수",     val: "340대",    color: C.bmwBlue, pct: 1.0 },
    { label: "서비스 매출",   val: "5.0억",    color: C.green,   pct: 1.0 },
    { label: "CSI 점수",      val: "92점 이상",color: C.gold,    pct: 1.0 },
    { label: "부품 매출",     val: "1.4억",    color: C.purple,  pct: 1.0 },
    { label: "재방문율",      val: "75%",      color: C.bmwBlueLt, pct: 1.0 },
  ];

  goals.forEach((g, i) => {
    const gy = 1.44 + i * 0.76;
    sl.addText(g.label, {
      x: 0.38, y: gy, w: 2.6, h: 0.32,
      fontSize: 10, bold: true, color: C.slate2,
      valign: "middle", fontFace: "Arial", margin: 0
    });
    sl.addText(g.val, {
      x: 3.0, y: gy, w: 1.65, h: 0.32,
      fontSize: 12, bold: true, color: g.color,
      align: "right", valign: "middle", fontFace: "Arial Black", margin: 0
    });
    // 바 배경
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.38, y: gy + 0.34, w: 4.25, h: 0.12,
      fill: { color: "1E2D4A" }, line: { color: "1E2D4A" }
    });
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.38, y: gy + 0.34, w: 4.25 * g.pct, h: 0.12,
      fill: { color: g.color }, line: { color: g.color }
    });
  });

  // ── 오른쪽: 특이사항/메모 ──
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 0.92, w: 4.5, h: 0.42,
    fill: { color: "0D1526" }, line: { color: C.border }
  });
  sl.addText("특이사항 · 메모", {
    x: 5.2, y: 0.92, w: 4.5, h: 0.42,
    fontSize: 11, bold: true, color: C.bmwBlueLt,
    charSpacing: 2, align: "center", valign: "middle",
    fontFace: "Arial", margin: 0
  });

  sl.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.42, w: 4.5, h: 3.9,
    fill: { color: C.cardBg }, line: { color: C.border, pt: 1 }
  });

  const memos = [
    "· 5월 에어컨 점검 시즌 사전 예약 캠페인 준비",
    "· 신규 SA 2명 온보딩 예정 (5월 2주차)",
    "· 본사 품질 감사 일정 확인 필요 (5월 중)",
    "· 주차 공간 포화 문제 → 탁송 서비스 확대 검토",
    "",
    "[ 추가 메모 입력란 ]",
    "___________________________________",
    "___________________________________",
    "___________________________________",
  ];

  sl.addText(memos.join("\n"), {
    x: 5.35, y: 1.55, w: 4.2, h: 3.65,
    fontSize: 10.5, color: C.slate2,
    valign: "top", fontFace: "Calibri",
    lineSpacingMultiple: 1.4, margin: 0
  });

  // 하단 다음 회의 안내
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 5.18, w: 9.4, h: 0.35,
    fill: { color: "0D1526" }, line: { color: C.border }
  });
  sl.addText("다음 회의: ______년 ______월 ______일 (    ) ______:______ / 장소: ____________________", {
    x: 0.3, y: 5.18, w: 9.4, h: 0.35,
    fontSize: 9.5, color: C.slate2, align: "center", valign: "middle",
    fontFace: "Calibri", margin: 0
  });
}

// ── 파일 저장 ──────────────────────────────────────────────
pres.writeFile({ fileName: "/Users/youngchulyu/바이브코딩/제작물/BMW_월간지점장회의_템플릿.pptx" })
  .then(() => console.log("✅ 저장 완료: BMW_월간지점장회의_템플릿.pptx"))
  .catch(e => console.error("❌ 오류:", e));
