// build_summary_pptx.js — 논문 요약 발표자료(10쪽) 생성
// 실행: (최초 1회) npm install pptxgenjs  →  node code/tools/build_summary_pptx.js
const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');

const ROOT = path.resolve(__dirname, '..', '..');
const FIG = path.join(ROOT, 'figures');
const OUT = path.join(ROOT, 'paper', '한국_인앱결제_LTA_요약_20261111.pptx');
const s1 = JSON.parse(fs.readFileSync(path.join(ROOT, 'outputs', 'prop1_summary.json'), 'utf8'));
const n = JSON.parse(fs.readFileSync(path.join(ROOT, 'outputs', 'paper_numbers.json'), 'utf8'));
const RR = JSON.parse(fs.readFileSync(path.join(ROOT, 'outputs', 'real_summary.json'), 'utf8'));   // 원자료 분석 결과
const RIV = RR.waves.slice(0, -1).map((a, i) => `${a}→${RR.waves[i + 1]}`);
const rman = (it, iv) => RR.manifest.find((x) => x.item === it && x.interval === iv);
const rcon = (tn, cn) => RR.contrasts.find((x) => x.transition === tn && x.contrast === cn);
const pct0 = (x) => (100 * x).toFixed(0);
const pct1 = (x) => (100 * x).toFixed(1);
const mc = (N, d) => n.mc.find((r) => r.N === N && Math.abs(r.delta - d) < 1e-9);
const pc = (x, k = 1) => (100 * x).toFixed(k);
const f1 = (x) => x.toFixed(1);

// ---- 색 ----
const NAVY = '1B2A41', INK = '1F2937', MUTED = '6B7280', LINE = 'E5E7EB', PANEL = 'F3F6FA';
const BLUE = '2A78D6', ORANGE = 'EB6834', GREEN = '1BAF7A', ICE = 'DCE8F7', WHITE = 'FFFFFF', RED = 'C0392B';
const FONT = '맑은 고딕';

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.333 x 7.5
pres.author = 'Korea In-App LTA project';
pres.title = '한국 인앱결제 강제금지 규제와 디지털 콘텐츠 소비 상태의 전이 — 요약';
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

const W = 13.333, M = 0.6;
let slideNo = 0;

function base(dark = false) {
  const s = pres.addSlide();
  slideNo += 1;
  s.background = { color: dark ? NAVY : WHITE };
  s.addText(String(slideNo), { x: W - 1.1, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: dark ? 'A9B4C6' : MUTED, align: 'right', margin: 0, isTextBox: true, fontFace: FONT });
  s.addText('한국 인앱결제 강제금지 규제와 디지털 콘텐츠 소비 상태의 전이 · 연구 요약', { x: M, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: dark ? 'A9B4C6' : MUTED, margin: 0, isTextBox: true, fontFace: FONT });
  return s;
}
function title(s, text, sub) {
  s.addText(text, { x: M, y: 0.45, w: W - 2 * M, h: 0.7, fontSize: 28, bold: true, color: NAVY, margin: 0, isTextBox: true, fontFace: FONT });
  if (sub) s.addText(sub, { x: M, y: 1.15, w: W - 2 * M, h: 0.4, fontSize: 14, color: MUTED, margin: 0, isTextBox: true, fontFace: FONT });
}
function bullets(s, items, opt) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: 8 } })),
    { fontSize: 14, color: INK, valign: 'top', margin: 0, isTextBox: true, fontFace: FONT, ...opt });
}
function stat(s, x, y, w, h, big, label, color) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: PANEL }, line: { color: LINE, width: 0.75 }, rectRadius: 0.08 });
  s.addText(big, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: h * 0.52, fontSize: 30, bold: true, color, margin: 0, isTextBox: true, valign: 'bottom', fontFace: FONT });
  s.addText(label, { x: x + 0.2, y: y + h * 0.62, w: w - 0.4, h: h * 0.36, fontSize: 11.5, color: MUTED, margin: 0, isTextBox: true, valign: 'top', fontFace: FONT });
}
function tag(s, x, y, w, text, color) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h: 0.32, fill: { color }, line: { color }, rectRadius: 0.16 });
  s.addText(text, { x, y, w, h: 0.32, fontSize: 11, bold: true, color: WHITE, align: 'center', valign: 'middle', margin: 0, isTextBox: true, fontFace: FONT });
}
const chartText = { catAxisLabelFontFace: FONT, valAxisLabelFontFace: FONT, dataLabelFontFace: FONT, legendFontFace: FONT, titleFontFace: FONT,
  catAxisLabelColor: INK, valAxisLabelColor: MUTED, catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, dataLabelFontSize: 10, dataLabelColor: INK,
  valGridLine: { color: LINE, size: 0.5 }, catGridLine: { style: 'none' }, legendFontSize: 11, legendColor: INK };

// ---------- 1. 표지 ----------
{
  const s = base(true);
  s.addText('한국 인앱결제 강제금지 규제와\n디지털 콘텐츠 소비 상태의 전이', { x: M, y: 1.5, w: W - 2 * M, h: 1.9, fontSize: 38, bold: true, color: WHITE, margin: 0, isTextBox: true, fontFace: FONT, valign: 'bottom' });
  s.addText('한국미디어패널 2020~2025년 원자료의 잠재전이분석 · 연구명제의 공개자료 검토', { x: M, y: 3.55, w: W - 2 * M, h: 0.5, fontSize: 18, color: ICE, margin: 0, isTextBox: true, fontFace: FONT });
  s.addText('연구 요약 · 2026년 11월 11일', { x: M, y: 4.25, w: 6, h: 0.4, fontSize: 14, color: 'A9B4C6', margin: 0, isTextBox: true, fontFace: FONT });
  const chips = [['플랫폼 규제', BLUE], ['한국미디어패널', GREEN], ['잠재전이분석', ORANGE]];
  chips.forEach(([t, c], i) => tag(s, M + i * 2.0, 5.1, 1.85, t, c));
}

// ---------- 2. 배경: 정책 연표 ----------
{
  const s = base();
  title(s, '배경: 세계 최초의 인앱결제 강제금지, 그러나 제재는 5년 뒤', '법 시행(2021-09)부터 과징금 의결(2026-10)까지 — 플랫폼의 최소 대응과 가격 인상이 사이에 놓인다');
  const ev = [
    ['2020-09', '구글, 인앱결제 의무 전면 확대 예고(수수료 30%)', BLUE],
    ['2021-09-14', '전기통신사업법 개정 시행: 특정 결제방식 강제 금지', NAVY],
    ['2021-12', '구글, 제3자 결제 허용 — 수수료 26%(4%p 인하)', BLUE],
    ['2022-04~06', '아웃링크 금지, 애플 26% 제3자 결제 · 콘텐츠 가격 10~20% 인상', ORANGE],
    ['2023-10', '방통위 시정조치안: 과징금 680억 원(의결 보류)', MUTED],
    ['2026-10-28', '과징금 637.1억 원 의결(구글 429, 애플 208.1) + 시정명령', GREEN],
  ];
  const x0 = M + 1.0, x1 = W - M - 1.0, y = 3.0;
  s.addShape(pres.ShapeType.line, { x: x0, y, w: x1 - x0, h: 0, line: { color: LINE, width: 2 } });
  const step = (x1 - x0) / (ev.length - 1);
  ev.forEach(([d, t, c], i) => {
    const cx = x0 + i * step;
    s.addShape(pres.ShapeType.ellipse, { x: cx - 0.13, y: y - 0.13, w: 0.26, h: 0.26, fill: { color: c }, line: { color: WHITE, width: 1.5 } });
    s.addText(d, { x: cx - 1.05, y: y - 0.75, w: 2.1, h: 0.4, fontSize: 13, bold: true, color: c, align: 'center', margin: 0, isTextBox: true, fontFace: FONT });
    s.addText(t, { x: cx - 0.9, y: y + 0.3, w: 1.8, h: 1.5, fontSize: 11, color: INK, align: 'center', valign: 'top', margin: 0, isTextBox: true, fontFace: FONT });
  });
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 5.0, w: W - 2 * M, h: 1.4, fill: { color: PANEL }, line: { color: LINE, width: 0.75 }, rectRadius: 0.08 });
  s.addText([
    { text: '문제의식  ', options: { bold: true, color: NAVY } },
    { text: '법은 앱마켓 사업자와 콘텐츠 사업자 사이의 수수료 배분을 겨냥했지만, 플랫폼은 법의 문언만 충족하는 선택지(26% 제3자 결제)를 내놓았고, 콘텐츠 사업자는 플랫폼 결제를 받아들여 그 비용을 가격으로 넘겼다. 그렇다면 그 부담의 종착점인 이용자의 유료 콘텐츠 소비는 어떻게 달라졌는가?' },
  ], { x: M + 0.25, y: 5.1, w: W - 2 * M - 0.5, h: 1.2, fontSize: 13.5, color: INK, valign: 'middle', margin: 0, isTextBox: true, fontFace: FONT });
}

// ---------- 3. 연구명제와 질문 ----------
{
  const s = base();
  title(s, '연구명제와 연구 질문: 플랫폼 → 사업자 → 이용자의 비용 전가 사슬', '명제 1·2는 공급 측(사업자 자료)으로, 연구 질문은 수요 측(패널·잠재전이분석)으로 검토한다');
  const boxes = [['앱마켓 플랫폼', '구글·애플\n결제 방식과 수수료 결정', BLUE], ['콘텐츠 사업자', 'OTT·음원·웹툰·게임\n결제전략 선택, 가격 결정', ORANGE], ['이용자', '유료 앱 · 앱 내 아이템\n영상 · 음악 구독의 소비 상태', GREEN]];
  const bw = 3.4, gap = 0.9, bx0 = (W - (3 * bw + 2 * gap)) / 2, by = 1.85;
  boxes.forEach(([h, d, c], i) => {
    const x = bx0 + i * (bw + gap);
    s.addShape(pres.ShapeType.roundRect, { x, y: by, w: bw, h: 1.25, fill: { color: PANEL }, line: { color: c, width: 1.5 }, rectRadius: 0.1 });
    s.addText(h, { x: x + 0.2, y: by + 0.12, w: bw - 0.4, h: 0.4, fontSize: 16, bold: true, color: c, margin: 0, isTextBox: true, fontFace: FONT });
    s.addText(d, { x: x + 0.2, y: by + 0.52, w: bw - 0.4, h: 0.65, fontSize: 12, color: INK, margin: 0, isTextBox: true, valign: 'top', fontFace: FONT });
    if (i < 2) s.addShape(pres.ShapeType.rightArrow, { x: x + bw + 0.15, y: by + 0.42, w: gap - 0.3, h: 0.4, fill: { color: 'B8C4D6' }, line: { color: 'B8C4D6' } });
  });
  const labels = ['수수료 · 결제 방식 강제', '가격 인상(비용 전가)'];
  labels.forEach((t, i) => s.addText(t, { x: bx0 + bw + i * (bw + gap) - 0.6, y: by + 1.3, w: gap + 1.2, h: 0.3, fontSize: 10.5, color: MUTED, align: 'center', margin: 0, isTextBox: true, fontFace: FONT }));
  const py = 3.75;
  s.addShape(pres.ShapeType.roundRect, { x: M, y: py, w: 6.0, h: 2.85, fill: { color: WHITE }, line: { color: LINE, width: 1 }, rectRadius: 0.08 });
  s.addText('연구명제 (공급 측)', { x: M + 0.25, y: py + 0.15, w: 5.5, h: 0.35, fontSize: 14, bold: true, color: NAVY, margin: 0, isTextBox: true, fontFace: FONT });
  s.addText([
    { text: '명제 1. ', options: { bold: true, color: ORANGE } },
    { text: '인앱결제 강제 금지 규제 시행 전후 앱마켓 관련 기업들의 사업 및 결제전략 유형에 변화가 나타날 것이다.', options: { breakLine: true, paraSpaceAfter: 10 } },
    { text: '명제 2. ', options: { bold: true, color: ORANGE } },
    { text: '규제 시행 이후 플랫폼 사업자의 전략적 대응에 따라 규제의 실질적 효과는 당초 정책목표와 다르게 나타날 수 있다.' },
  ], { x: M + 0.25, y: py + 0.55, w: 5.5, h: 2.2, fontSize: 13, color: INK, valign: 'top', margin: 0, isTextBox: true, fontFace: FONT });
  const qx = M + 6.35;
  s.addShape(pres.ShapeType.roundRect, { x: qx, w: W - M - qx, y: py, h: 2.85, fill: { color: WHITE }, line: { color: LINE, width: 1 }, rectRadius: 0.08 });
  s.addText('연구 질문 (수요 측, 잠재전이분석)', { x: qx + 0.25, y: py + 0.15, w: 5.6, h: 0.35, fontSize: 14, bold: true, color: NAVY, margin: 0, isTextBox: true, fontFace: FONT });
  bullets(s, [
    '이용자의 유료 콘텐츠 소비는 몇 개의 잠재 상태(저소비 / 구독 중심 / 복합 구매)로 요약되는가?',
    '상태 간 전이확률은 규제·가격 인상 시기(2022~23년)를 전후로 달라졌는가? — 특히 복합 구매에서 구독 중심·저소비로 내려가는 전이',
    '그 변화는 가격 인상에 더 많이 노출된 이용자에게서 더 컸는가?',
  ], { x: qx + 0.25, y: py + 0.55, w: W - M - qx - 0.5, h: 2.2, fontSize: 12.5 });
}

// ---------- 4. 자료와 방법 ----------
{
  const s = base();
  title(s, '자료와 방법: 공개자료 코딩 + 패널 원자료 + 모의자료 검증', '이용자 측의 주 분석은 한국미디어패널 개인 원자료. 모의자료는 분석 절차를 사전에 검증하는 데 사용');
  const cards = [
    ['A', '실제 공개자료', BLUE, ['정책 연표(공식 문서·보도, 출처 URL)', `사업자 결제전략 코딩: ${s1.n_services}개 콘텐츠 서비스 + ${s1.n_market_operators}개 앱마켓(규제 전후 안드로이드 결제 방식·대표 상품 가격)`, '정책목표 대비 결과 증거 48건', '「2021~2025 한국미디어패널조사」 5개 연도 공표 집계치·유지율']],
    ['B', '개인 원자료(실제)', GREEN, [`한국미디어패널 2020~2025년, ${RR.n_persons.toLocaleString()}명 · ${RR.n_households.toLocaleString()}가구`, '지표 4개: 유료 앱 · 앱 내 아이템 · 영상 유료 이용 · 음악 유료 이용(지출이 있는 경우만)', '잠재전이분석(3개 상태), 영상 문항만 2024년부터 따로 추정', '가중 추정, 가구 군집 부트스트랩, 모형 없는 관측 전이율 병행']],
    ['C', '모의자료 검증', ORANGE, [`설계 보정 모의패널 N = ${n.run.n_persons.toLocaleString()}: 정답을 심어 두고 되찾는지 확인`, '파이썬 · R · LMest 3중 대조', '몬테카를로: 전이 변화 Δ와 표본 크기별 검정력', '규제 강도 공변량 모형의 사전 시험']],
  ];
  const cw = (W - 2 * M - 2 * 0.4) / 3;
  cards.forEach(([k, h, c, items], i) => {
    const x = M + i * (cw + 0.4), y = 1.85;
    s.addShape(pres.ShapeType.roundRect, { x, y, w: cw, h: 4.2, fill: { color: PANEL }, line: { color: LINE, width: 0.75 }, rectRadius: 0.1 });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.25, y: y + 0.25, w: 0.55, h: 0.55, fill: { color: c }, line: { color: c } });
    s.addText(k, { x: x + 0.25, y: y + 0.25, w: 0.55, h: 0.55, fontSize: 16, bold: true, color: WHITE, align: 'center', valign: 'middle', margin: 0, isTextBox: true, fontFace: FONT });
    s.addText(h, { x: x + 0.95, y: y + 0.25, w: cw - 1.2, h: 0.55, fontSize: 16, bold: true, color: NAVY, valign: 'middle', margin: 0, isTextBox: true, fontFace: FONT });
    bullets(s, items, { x: x + 0.25, y: y + 1.05, w: cw - 0.5, h: 3.0, fontSize: 13.5 });
  });
}

// ---------- 5. 명제 1 결과 ----------
{
  const s = base();
  title(s, `명제 1 지지: ${s1.payment_changed.k}/${s1.payment_changed.n} 서비스가 자체 결제에서 플랫폼 결제 수용으로`, '규제 전후 결제 방식 비교가 가능한 19개 콘텐츠 서비스(영상·음원·웹툰·게임·메신저), 공개 보도·공식 문서 코딩');
  stat(s, M, 1.85, 2.85, 1.55, `${pc(s1.payment_changed.share)}%`, `결제 방식 변경 (${s1.payment_changed.k}/${s1.payment_changed.n}; 95% CI ${pc(s1.payment_changed.ci95[0], 0)}–${pc(s1.payment_changed.ci95[1], 0)}%)`, BLUE);
  stat(s, M + 3.05, 1.85, 2.85, 1.55, `${s1.iap_use_pre.k} → ${s1.iap_use_post.k}`, `구글 인앱결제 이용 서비스 수 (McNemar p = ${s1.mcnemar.p_exact.toFixed(4)})`, BLUE);
  stat(s, M, 3.6, 2.85, 1.55, `${s1.price_raised.k}/${s1.price_raised.n}`, `2022년 인앱 가격 변경 서비스 전부 인상 (부호검정 p = ${s1.sign_test_p.toFixed(3)})`, ORANGE);
  stat(s, M + 3.05, 3.6, 2.85, 1.55, `${s1.third_party_adopted.k}/${s1.third_party_adopted.n}`, '제3자 결제(26%) 도입 — FLO 1개뿐', GREEN);
  s.addText('규제 전 12개 서비스의 결제 방식은 구글의 2020년 9월 정책 공지와 보도(수수료 8~9% 자체 결제)로 추론 부여함. 변화의 직접 계기는 법보다 구글의 인앱결제 의무화와 아웃링크 금지 조치임.', { x: M, y: 5.35, w: 5.9, h: 0.9, fontSize: 10.5, color: MUTED, margin: 0, isTextBox: true, fontFace: FONT, valign: 'top' });
  const cats = Object.keys(s1.post_type_counts);
  const vals = cats.map((k) => s1.post_type_counts[k]);
  s.addChart(pres.ChartType.bar, [{ name: '서비스 수', labels: cats, values: vals }], {
    x: 6.9, y: 1.75, w: W - M - 6.9, h: 4.1, barDir: 'bar', chartColors: [ORANGE, 'F3A683', BLUE, GREEN, MUTED], ...chartText,
    showTitle: true, title: '규제 후 결제전략 유형 (19개 서비스)', titleFontSize: 13, titleColor: NAVY,
    showValue: true, dataLabelPosition: 'outEnd', showLegend: false, valAxisHidden: true, valGridLine: { style: 'none' },
    catAxisLabelFontSize: 11, barGapWidthPct: 45, valAxisMaxVal: 12,
  });
  s.addText(`규제 전: 앱 내 자체결제 ${s1.pre_type_counts['앱 내 자체결제']} · 구글 인앱결제 ${s1.pre_type_counts['구글 인앱결제']} · 웹 전용 ${s1.pre_type_counts['앱 내 결제 없음(웹 전용)']}`, { x: 6.9, y: 5.95, w: W - M - 6.9, h: 0.35, fontSize: 11, color: MUTED, margin: 0, isTextBox: true, fontFace: FONT });
}

// ---------- 6. 가격 전가 ----------
{
  const s = base();
  title(s, '가격 인상 폭은 10~20%: 수수료의 상당 부분이 이용자에게 전가됨', '2022년 안드로이드 인앱 가격을 올린 10개 서비스. 손익분기 수수료율 f* = 1 − P(이전)/P(이후)');
  const rows = [
    ['네이버웹툰(쿠키)', 20.0], ['네이버 시리즈(쿠키)', 20.0], ['카카오페이지·웹툰(캐시)', 20.0], ['리디(캐시)', 20.0],
    ['카카오톡 이모티콘 플러스', 16.33], ['시즌(seezn)', 14.55], ['웨이브', 13.92], ['티빙', 13.92], ['FLO', 13.92], ['멜론', 10.13],
  ].reverse();
  s.addChart(pres.ChartType.bar, [{ name: '가격 인상률(%)', labels: rows.map((r) => r[0]), values: rows.map((r) => r[1]) }], {
    x: M, y: 1.7, w: 7.0, h: 4.9, barDir: 'bar', chartColors: [ORANGE], ...chartText,
    showTitle: true, title: '2022년 인앱 가격 인상률(%)', titleFontSize: 13, titleColor: NAVY,
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0.0', showLegend: false, valAxisHidden: true, valGridLine: { style: 'none' },
    barGapWidthPct: 40, valAxisMaxVal: 25, valAxisMinVal: 0,
  });
  const rx = M + 7.4, rw = W - M - rx;
  stat(s, rx, 1.85, rw, 1.3, `중위 ${f1(s1.price_change_pct_raised.median)}%`, `인상률 평균 ${f1(s1.price_change_pct_raised.mean)}%, 범위 ${f1(s1.price_change_pct_raised.min)}–${f1(s1.price_change_pct_raised.max)}%`, ORANGE);
  stat(s, rx, 3.3, rw, 1.3, `f* 중위 ${f1(s1.breakeven_fee_pct_raised.median)}%`, `인상분이 상쇄하는 수수료율(범위 ${f1(s1.breakeven_fee_pct_raised.min)}–${f1(s1.breakeven_fee_pct_raised.max)}%). 수수료 15%의 완전 전가 = ${f1(s1.full_passthrough_rise_pct.fee15)}% 인상, 30% = ${f1(s1.full_passthrough_rise_pct.fee30)}%`, NAVY);
  stat(s, rx, 4.75, rw, 1.3, `${s1.web_price_kept.k}/${s1.web_price_kept.n}`, '가격 확인 서비스 모두 PC·웹 가격은 유지 → 인상은 앱마켓 수수료에 귀속되는 "앱 내 결제 할증"', GREEN);
  s.addText('유튜브 프리미엄(2023-12, +42.6%)은 2022년 창 밖이라 통계에서 제외.', { x: M, y: 6.6, w: 7, h: 0.3, fontSize: 10, color: MUTED, margin: 0, isTextBox: true, fontFace: FONT });
}

// ---------- 7. 명제 2: 정책목표 대비 결과 ----------
{
  const s = base();
  title(s, '명제 2 지지: 결제 선택권은 형식적으로만 달성, 수수료·후생은 역행', '정책목표별 결과 지표(공개 증거 48건) — 플랫폼의 전략적 대응이 규제의 실질 효과를 바꾸었다');
  const rows = [
    ['결제 선택권 보장', '제3자 결제 허용(구글·애플 26%), 아웃링크 금지(2022-06)', '제3자 결제 도입 1/19 — 수수료 26% + PG 3%대로 인앱결제보다 불리', '형식적 달성, 실질 미달', ORANGE],
    ['수수료 인하·경쟁 촉진', '인하 폭 4%p에 그침, 인앱결제 이용 서비스 5 → 17', '구글 수수료 추정 시나리오: 8,331억 vs 4,193억 원(2021~, 방통위·KISA)', '역행', RED],
    ['이용자 후생', '2022년 콘텐츠 가격 10~20% 인상, 웹 가격은 유지', '소비자 추가 부담 추정 2,300억~3,500억 원/년(국회·업계)', '역행', RED],
    ['규제 집행', '2023-10 시정조치안 680억 → 2026-10-28 과징금 637.1억 의결', '법 시행 후 5년 1개월, 과징금은 산출액 약 4,800억에서 법정 상한 적용으로 축소', '지연, 제한적', ORANGE],
    ['공급 측 성과(앱 산출·진입)', 'Chang & Miller(2025) DiD: 0.002(SE .064) / −0.093(.079)', '통계적으로 유의한 변화 없음', '변화 없음', MUTED],
  ];
  const cols = [2.3, 3.9, 4.0, 1.9];
  const head = ['정책목표', '플랫폼·사업자의 대응', '관찰된 결과', '평가'];
  const tbl = [head.map((h) => ({ text: h, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 12, align: 'center', valign: 'middle', fontFace: FONT } }))];
  rows.forEach(([g, r, o, v, c], i) => {
    const fill = i % 2 ? WHITE : PANEL;
    tbl.push([
      { text: g, options: { bold: true, color: NAVY, fill: { color: fill }, fontSize: 11.5, valign: 'middle', fontFace: FONT } },
      { text: r, options: { color: INK, fill: { color: fill }, fontSize: 11, valign: 'middle', fontFace: FONT } },
      { text: o, options: { color: INK, fill: { color: fill }, fontSize: 11, valign: 'middle', fontFace: FONT } },
      { text: v, options: { bold: true, color: c, fill: { color: fill }, fontSize: 11.5, align: 'center', valign: 'middle', fontFace: FONT } },
    ]);
  });
  s.addTable(tbl, { x: M, y: 1.8, w: W - 2 * M, colW: cols, rowH: [0.42, 0.78, 0.78, 0.78, 0.78, 0.78], border: { type: 'solid', color: LINE, pt: 0.75 }, margin: 0.08 });
}

// ---------- 8. 이용자 측: 공표 집계 + LTA 검증 ----------
{
  const s = base();
  title(s, '절차 검증: 모의패널에서 3개 소비 상태를 정확히 복원', '한국미디어패널 공표치(실제) · 설계 보정 모의패널의 잠재전이분석(절차 검증)');
  stat(s, M, 1.85, 2.75, 1.4, '5.4%', '2025년 스마트 기기 이용자의 유료 앱 구입 경험률(공표)', BLUE);
  stat(s, M + 2.95, 1.85, 2.75, 1.4, '15.4%', '앱 내 아이템 구입 경험률(공표) — 연령에 따라 급격히 감소', BLUE);
  stat(s, M, 3.4, 2.75, 1.4, '84.8%', '2024년 패널 유지율(공표) — 탈락 처리가 전이 추정의 관건', GREEN);
  stat(s, M + 2.95, 3.4, 2.75, 1.4, 'K = 3', `BIC가 선택한 상태 수: 저소비 · 구독 중심 · 복합 구매 (응답확률 오차 ≤ ${n.run.max_abs_err.theta.toFixed(3)})`, ORANGE);
  bullets(s, [
    `모의패널 N = ${n.run.n_persons.toLocaleString()}, 5개 조사연도: 상태 프로파일과 전이행렬을 참값에 가깝게 복원(전이확률 최대 오차 ${n.run.max_abs_err.A.toFixed(3)})`,
    '파이썬 엔진 · R 독립 구현 · LMest 패키지의 로그우도가 소수 셋째 자리까지 일치',
    '측정 불변성, 이변량 잔차, 분류 진단 통과 — 실제 원자료를 넣을 준비가 된 절차',
  ], { x: M, y: 5.0, w: 5.7, h: 1.8, fontSize: 12 });
  s.addImage({ path: path.join(FIG, 'fig05_response_profiles.png'), x: 6.6, y: 1.8, w: 6.1, h: 6.1 * 792 / 1425 });
  s.addText('그림. 상태별 응답확률 프로파일(모의패널, 참값 대비)', { x: 6.6, y: 1.85 + 6.1 * 792 / 1425 + 0.05, w: 6.1, h: 0.3, fontSize: 10.5, color: MUTED, align: 'center', margin: 0, isTextBox: true, fontFace: FONT });
}

// ---------- 9. 검정력 ----------
{
  const s = base();
  title(s, '검정력: 0.06의 전이 변화는 N = 8,000에서도 1/3만 검출', '몬테카를로 200회 반복, 유의수준 5%. 전이확률의 시기별 변화 Δ를 검출할 확률');
  const deltas = [0, 0.03, 0.06, 0.1];
  const lab = deltas.map((d) => `Δ = ${d.toFixed(2)}`);
  const series = [
    { name: 'N=8,000 초점 검정', values: deltas.map((d) => mc(8000, d).reject_rate_regime) },
    { name: 'N=8,000 총괄 검정', values: deltas.map((d) => mc(8000, d).reject_rate) },
    { name: 'N=2,000 초점 검정', values: deltas.map((d) => mc(2000, d).reject_rate_regime) },
    { name: 'N=2,000 총괄 검정', values: deltas.map((d) => mc(2000, d).reject_rate) },
  ].map((x) => ({ ...x, labels: lab }));
  s.addChart(pres.ChartType.line, series, {
    x: M, y: 1.7, w: 7.4, h: 4.9, chartColors: [BLUE, '9DC1EE', ORANGE, 'F5B99A'], lineSize: 2.25, lineDataSymbol: 'circle', lineDataSymbolSize: 7, ...chartText,
    showTitle: true, title: '전이 변화 검출 확률(검정력)', titleFontSize: 13, titleColor: NAVY,
    showLegend: true, legendPos: 'b', valAxisMinVal: 0, valAxisMaxVal: 1, valAxisMajorUnit: 0.2, valAxisLabelFormatCode: '0.0',
  });
  const rx = M + 7.8, rw = W - M - rx;
  stat(s, rx, 1.85, rw, 1.3, f3p(mc(8000, 0.06).reject_rate_regime), 'N = 8,000, Δ = 0.06 — 초점 검정의 검정력 (총괄 검정 ' + f3p(mc(8000, 0.06).reject_rate) + ')', BLUE);
  stat(s, rx, 3.3, rw, 1.3, f3p(mc(8000, 0.10).reject_rate_regime), 'N = 8,000, Δ = 0.10 — 초점 검정 (총괄 검정 ' + f3p(mc(8000, 0.10).reject_rate) + ')', BLUE);
  bullets(s, [
    '실제 분석에서는 변화 시점(2022년)을 사전 지정한 초점 검정을 쓴다',
    '유의하지 않은 결과를 "효과 없음"으로 읽지 않는다',
    '공변량(연령·기기)과 추가 지표로 정보를 보강한다',
  ], { x: rx, y: 4.8, w: rw, h: 1.9, fontSize: 12 });
}
function f3p(x) { return x.toFixed(2); }

// ---------- 10. 재검증 ----------
{
  const rv = JSON.parse(fs.readFileSync(path.join(ROOT, 'outputs', 'reval_summary.json'), 'utf8'));
  const ia = rv.real_series_pct.inapp_item, af = rv.aggregate_fit, pw = rv.scenario_b2.power_omnibus['500'];
  const s = base();
  title(s, '재검증: 실제 앱 구매율은 2022~23년 급락 후 회복', '2021~2025년 보고서 5권의 공표 수치(전체 응답자 대비)는 모의패널 설계의 가정과 다르다. 옮겨 쓴 수치 30건은 모두 원문과 일치');
  const iw = 6.7;
  s.addImage({ path: path.join(FIG, 'fig10_real_series_vs_design.png'), x: M, y: 1.7, w: iw, h: iw * 6.8 / 9.2 });
  const rx = M + iw + 0.4, rw = W - M - rx;
  stat(s, rx, 1.8, rw, 1.2, `${f1(ia[0])} → ${f1(ia[2])} → ${f1(ia[3])}%`, '앱 내 아이템 구입 경험률: 2021 → 2023 → 2024년', BLUE);
  stat(s, rx, 3.1, rw, 1.2, `${f1(af.homogeneous.max_abs_resid_pp)}%p`, `전이가 시기마다 같다는 모형의 최소 오차(표본오차 ${f1(af.typical_sampling_se_pp)}%p) — 실제 궤적과 양립 불가`, ORANGE);
  stat(s, rx, 4.4, rw, 1.2, `${Math.round(pw.reject_rate * pw.reps)}/${pw.reps}`, '실제 크기의 변화라면 동질성 검정은 N = 500에서도 전부 기각', GREEN);
  bullets(s, [
    '2023→24년에 세 지표가 동시 급등(문항 동일, 유지율 84.8%) — 측정 단절 가능성',
    '2021년은 코로나 시기 고점일 수 있음 → 규제 효과로 해석 불가',
    '먼저 풀 문제는 검정력보다 연도 간 측정 동등성',
  ], { x: rx, y: 5.75, w: rw, h: 1.15, fontSize: 11.5 });
}

// ---------- 11. 규제 강도 공변량 모형 ----------
{
  const cv = JSON.parse(fs.readFileSync(path.join(ROOT, 'outputs', 'cov_summary.json'), 'utf8'));
  const sp = cv.sector_price_increase_pct, fi = cv.focus_interaction;
  const mcv = (N, alt) => cv.monte_carlo.find((x) => Number(x.N) === N && Boolean(x.alt) === alt);
  const bigN = Math.max(...cv.monte_carlo.map((x) => Number(x.N))), smallN = Math.min(...cv.monte_carlo.map((x) => Number(x.N)));
  const s = base();
  title(s, '규제 강도: 가격 인상 노출 지수를 전이확률의 공변량으로', '초기 상태와 전이확률의 다항 로짓. 이 쪽은 모의자료에 의한 사전 시험이며, 원자료 결과는 뒤쪽에 있음');
  const lw = 4.55;
  const cards = [
    ['주 변인', ORANGE, '가격 인상 노출 지수', `기준 시점에 이용한 서비스 유형 × 2022년 인앱 가격 인상률의 합(영상 ${f1(sp.video)}%, 음원 ${f1(sp.music)}%, 웹툰 ${f1(sp.webtoon)}%, 게임 0%)`],
    ['보조 변인', BLUE, '스마트폰 운영체제', '안드로이드 1, iOS 0. 모의자료에서는 표준오차가 커서 효과를 검출하지 못함'],
    ['시기 통제', GREEN, '정책 단계(0~4)', '구간별 전이 절편으로 흡수. 관심 모수는 뒤 국면 계수 − 앞 국면 계수(국면 × 노출 상호작용)'],
  ];
  cards.forEach(([chip, col, name, desc], i) => {
    const y = 1.8 + i * 1.6;
    s.addShape(pres.ShapeType.roundRect, { x: M, y, w: lw, h: 1.45, fill: { color: PANEL }, line: { color: LINE, width: 0.75 }, rectRadius: 0.08 });
    tag(s, M + 0.2, y + 0.17, 1.05, chip, col);
    s.addText(name, { x: M + 1.4, y: y + 0.12, w: lw - 1.6, h: 0.42, fontSize: 14, bold: true, color: NAVY, valign: 'middle', margin: 0, isTextBox: true, fontFace: FONT });
    s.addText(desc, { x: M + 0.2, y: y + 0.62, w: lw - 0.4, h: 0.75, fontSize: 11.5, color: INK, valign: 'top', margin: 0, isTextBox: true, fontFace: FONT });
  });
  const rx = M + lw + 0.3, rw = W - M - rx;
  const ih = rw * 3.9 / 10.2;
  s.addImage({ path: path.join(FIG, 'fig11_covariate_transitions.png'), x: rx, y: 1.75, w: rw, h: ih });
  const ty = 1.75 + ih + 0.2, tw = (rw - 0.4) / 3, th = 6.45 - ty;
  stat(s, rx, ty, tw, th, fi.estimate.toFixed(3), `상호작용 추정값(심어 둔 ${fi.true.toFixed(2)}), p = ${fi.p.toFixed(3)}`, ORANGE);
  stat(s, rx + tw + 0.2, ty, tw, th, mcv(bigN, true).wald_reject.toFixed(2), `N = ${bigN.toLocaleString()} 검정력(왈드). 우도비 검정은 ${mcv(bigN, true).lr_reject.toFixed(2)}`, BLUE);
  stat(s, rx + 2 * (tw + 0.2), ty, tw, th, mcv(smallN, true).wald_reject.toFixed(2), `N = ${smallN.toLocaleString()} 검정력. 작은 표본에서는 부족`, MUTED);
}

// ---------- 12. 원자료: 상태와 비중 ----------
{
  const O = RR.main.occupancy;
  const s = base();
  title(s, `원자료 ${RR.n_persons.toLocaleString()}명: 세 소비 상태, 복합 구매는 2022~23년에 감소`, '한국미디어패널 개인 원자료 2020~2025년, 가중 추정. 영상 문항만 2024년부터 응답확률을 따로 추정');
  const iw = 8.3;
  s.addImage({ path: path.join(FIG, 'fig12_real_states.png'), x: M, y: 1.75, w: iw, h: iw * 4.2 / 10.2 });
  const rx = M + iw + 0.3, rw = W - M - rx;
  stat(s, rx, 1.75, rw, 1.1, `${pct1(O[1][2])} → ${pct1(O[3][2])}%`, '복합 구매 상태 비중, 2021 → 2023년', ORANGE);
  stat(s, rx, 2.95, rw, 1.1, `${pct0(O[0][0])} → ${pct0(O[5][0])}%`, '저소비 상태: 2020 → 2025년', BLUE);
  stat(s, rx, 4.15, rw, 1.1, `${pct0(O[0][1])} → ${pct0(O[5][1])}%`, '구독 중심 상태: 2020 → 2025년', GREEN);
  bullets(s, [
    '저소비: 네 지표 모두 거의 없음 / 구독 중심: 영상·음악 유료 이용 / 복합 구매: 앱 내 아이템·유료 앱까지 구입',
    'BIC는 상태를 더 잘게 나눈 모형을 선호 — 세 상태는 해석을 위해 고른 요약(네 상태 모형은 민감도 분석)',
    '2024년에 여러 문항에서 지출 응답이 한꺼번에 늘어, 측정이 달라졌을 가능성을 모형에 반영',
  ], { x: M, y: 5.45, w: W - 2 * M, h: 1.4, fontSize: 12.5 });
}

// ---------- 13. 원자료: 전이와 해석 ----------
{
  const A = RR.main.A;
  const c1 = rcon('복합 구매 → 구독 중심', '가격 인상기 − 이전');
  const mp = RIV.map((iv) => rman('paid_music', iv).persist);
  const s = base();
  title(s, '앱 구매 이탈은 가격 인상기에 집중, 값이 오른 구독은 유지', '복합 구매 상태의 전이확률(모형)과 앱 내 아이템 구입의 지속률(모형 없이 계산)이 같은 모양');
  const iw = 8.3;
  s.addImage({ path: path.join(FIG, 'fig13_real_transitions.png'), x: M, y: 1.75, w: iw, h: iw * 4.2 / 10.2 });
  const rx = M + iw + 0.3, rw = W - M - rx;
  stat(s, rx, 1.75, rw, 1.1, `${A[0][2][2].toFixed(2)} → ${A[1][2][2].toFixed(2)}`, '복합 구매 유지확률, 2020→21 대 2021→22', ORANGE);
  stat(s, rx, 2.95, rw, 1.1, `+${c1.estimate.toFixed(2)}`, '복합 → 구독 이동확률, 가격 인상기 − 이전', ORANGE);
  stat(s, rx, 4.15, rw, 1.1, `${pct0(Math.min(...mp))}~${pct0(Math.max(...mp))}%`, '음악 유료 이용 지속률(전 구간)', GREEN);
  bullets(s, [
    '2021년은 앱 내 구매와 게임 이용이 일시적으로 높았던 해 — 2021→22년의 이탈에는 그 반동이 들어 있음',
    '2022년에 값이 오른 영상·음원의 유료 이용은 줄지 않음 → 수수료 부담이 이용 중단보다 지출 증가로 돌아갔을 가능성',
    '결제 경로를 관측하지 못하고 2024년 측정이 달라져, 시기에 따른 차이를 규제의 인과효과로 읽을 수 없음',
  ], { x: M, y: 5.45, w: W - 2 * M, h: 1.4, fontSize: 12.5 });
}

// ---------- 14. 결론 ----------
{
  const s = base(true);
  s.addText('결론: 비용은 이용자에게 넘어갔고, 이용자는 구독을 유지했다', { x: M, y: 0.5, w: W - 2 * M, h: 0.8, fontSize: 28, bold: true, color: WHITE, margin: 0, isTextBox: true, fontFace: FONT });
  const cols = [
    ['두 명제는 지지된다', BLUE, ['19개 중 16개 서비스가 자체 결제 → 플랫폼 결제 수용', '2022년 가격 변경 10/10 인상(중위 15.4%), 웹 가격 유지', '제3자 결제 도입 1개 — 결제 선택권은 형식에 그침', '수수료·후생 지표는 정책목표와 반대 방향']],
    ['원자료가 보여 준 것', GREEN, [`세 상태 확인: 저소비 ${pct0(RR.main.occupancy[0][0])} → ${pct0(RR.main.occupancy[5][0])}%, 구독 중심 ${pct0(RR.main.occupancy[0][1])} → ${pct0(RR.main.occupancy[5][1])}%`, `복합 구매 유지확률 ${RR.main.A[0][2][2].toFixed(2)} → ${RR.main.A[1][2][2].toFixed(2)} → ${RR.main.A[2][2][2].toFixed(2)} → ${RR.main.A[3][2][2].toFixed(2)}`, '값이 오른 영상·음원의 유료 이용은 줄지 않음', '가격 인상의 효과로 돌리기는 어려움: 2021년 고점, 2024년 측정 변화']],
    ['한계와 다음 단계', ORANGE, ['시기에 따른 차이는 규제의 인과효과가 아님', '결제 경로와 지불 가격을 관측하지 못함', '상태 수 선택과 2024년 처리에 판단이 들어감', '2026년 시정명령 이후 조사와 결제 경로 문항으로 재검토']],
  ];
  const cw = (W - 2 * M - 2 * 0.4) / 3;
  cols.forEach(([h, c, items], i) => {
    const x = M + i * (cw + 0.4), y = 1.75;
    s.addShape(pres.ShapeType.roundRect, { x, y, w: cw, h: 4.4, fill: { color: '24364F' }, line: { color: '35516F', width: 0.75 }, rectRadius: 0.1 });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.25, y: y + 0.28, w: 0.22, h: 0.22, fill: { color: c }, line: { color: c } });
    s.addText(h, { x: x + 0.6, y: y + 0.15, w: cw - 0.8, h: 0.5, fontSize: 16, bold: true, color: WHITE, valign: 'middle', margin: 0, isTextBox: true, fontFace: FONT });
    s.addText(items.map((t, j) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: j < items.length - 1, paraSpaceAfter: 9 } })),
      { x: x + 0.25, y: y + 0.85, w: cw - 0.5, h: 3.4, fontSize: 13.5, color: 'E6ECF5', valign: 'top', margin: 0, isTextBox: true, fontFace: FONT });
  });
}

pres.writeFile({ fileName: OUT }).then(() => console.log('written', OUT));
