// build_paper.js — 논문 워드 파일 생성
// 실행: (최초 1회) npm install docx  →  python code/tools/collect_numbers.py  →  node code/tools/build_paper.js
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, Footer, PageNumber, BorderStyle,
} = require('docx');
const h = require('./docx_helpers');

const ROOT = path.resolve(__dirname, '..', '..');
const FIG = path.join(ROOT, 'figures');
const n = JSON.parse(fs.readFileSync(path.join(ROOT, 'outputs', 'paper_numbers.json'), 'utf8'));
const rv = JSON.parse(fs.readFileSync(path.join(ROOT, 'outputs', 'reval_summary.json'), 'utf8'));
const ia = rv.real_series_pct.inapp_item.map((v) => v.toFixed(1));
const rr = JSON.parse(fs.readFileSync(path.join(ROOT, 'outputs', 'real_summary.json'), 'utf8'));
const rA = rr.main.A, rO = rr.main.occupancy;
const rcon = (tn, cn) => rr.contrasts.find((x) => x.transition === tn && x.contrast === cn);
const rman = (it, iv) => rr.manifest.find((x) => x.item === it && x.interval === iv);
const RIV = rr.waves.slice(0, -1).map((a, i) => `${a}→${rr.waves[i + 1]}`);
const f2 = (x) => num(x, 2);
const pc1 = (x) => (100 * x).toFixed(1);
const cHB = rcon('복합 구매 → 구독 중심', '가격 인상기 − 이전');
const musicP = RIV.map((iv) => rman('paid_music', iv).persist);
const OUT = process.env.PAPER_OUT || path.join(ROOT, 'paper', '한국_인앱결제_LTA_논문_20261111.docx');

const { P, runs, HEAD_FONT, BODY_FONT, num, comma } = h;
const mc = (N, d) => n.mc.find((r) => r.N === N && Math.abs(r.delta - d) < 1e-9);
const f3 = (x) => num(x, 3);
const center = (text, opt = {}) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: opt.before || 0, after: opt.after === undefined ? 120 : opt.after, line: opt.line || 340 },
  children: runs(text, { font: opt.font || HEAD_FONT, size: opt.size || 21, bold: opt.bold, color: opt.color }),
});
const rule = () => new Paragraph({ spacing: { before: 60, after: 160 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: '000000', space: 1 } }, children: [] });

const front = [
  center('한국 인앱결제 강제금지 규제와 디지털 콘텐츠 소비 상태의 전이', { size: 30, bold: true, before: 200, after: 80, line: 420 }),
  center('한국미디어패널 2020~2025년 원자료의 잠재전이분석', { size: 25, bold: true, after: 260, line: 400 }),
  center('[저자명 · 소속 기입]', { size: 20, color: '777777', after: 60 }),
  center('2026년 11월 11일', { size: 19, color: '555555', after: 200 }),
  rule(),
  new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: '국문초록', font: HEAD_FONT, size: 22, bold: true })] }),
  P('한국은 2021년 전기통신사업법을 개정하여 앱마켓 사업자의 특정 결제방식 강제를 세계 최초로 금지하였다. 그러나 플랫폼은 수수료를 소폭 낮춘 제3자 결제만을 허용하는 방식으로 대응하였고, 2022년에는 주요 콘텐츠의 앱 내 결제 가격이 인상되었으며, 규제 당국의 첫 제재는 2026년 10월에야 의결되었다. 본 연구는 이 규제가 시행된 시기에 이용자의 유료 디지털 콘텐츠 소비가 어떻게 달라졌는지를 한국미디어패널조사의 개인 원자료와 잠재전이분석으로 검토한다.', { size: 20, line: 340 }),
  P('두 가지 연구명제를 설정하였다. 규제 시행 전후 앱마켓 관련 기업의 사업·결제전략 유형에 변화가 나타날 것이며(명제 1), 플랫폼의 전략적 대응에 따라 규제의 실질적 효과는 정책목표와 다르게 나타날 수 있다(명제 2)는 것이다. 공개 보도와 공식 문서에서 코딩한 사업자 자료에서 결제 방식을 전후 비교할 수 있었던 19개 콘텐츠 서비스 중 16개가 앱 내 자체 결제에서 플랫폼 결제의 수용으로 옮겨 갔고, 2022년 인앱 가격 변경이 확인된 10개 서비스는 모두 가격을 올렸으며(중위 15.4%), 제3자 결제를 도입한 서비스는 1개였다. 결제 선택권의 보장이라는 목표는 형식에 그쳤고 개발사 부담과 이용자 가격은 반대 방향으로 움직여 두 명제는 지지되었다.', { size: 20, line: 340 }),
  P(`이용자 측은 한국미디어패널 개인 원자료 2020~2025년(${comma(rr.n_persons)}명, ${comma(rr.n_households)}가구)으로 분석하였다. 유료 앱 구입, 앱 내 아이템 구입, 영상과 음악의 유료 이용이라는 네 지표에서 저소비, 구독 중심, 복합 구매의 세 상태가 추정되었다. 저소비 상태는 2020년 ${pc1(rO[0][0])}%에서 2025년 ${pc1(rO[5][0])}%로 줄고 구독 중심 상태가 늘었으며, 복합 구매 상태는 2021년 ${pc1(rO[1][2])}%에서 2023년 ${pc1(rO[3][2])}%로 줄었다가 2024년 ${pc1(rO[4][2])}%가 되었다. 복합 구매 상태에 머물 확률은 2020→2021년 ${f2(rA[0][2][2])}에서 2021→2022년 ${f2(rA[1][2][2])}, 2022→2023년 ${f2(rA[2][2][2])}로 낮아졌다가 이후 ${f2(rA[3][2][2])}, ${f2(rA[4][2][2])}로 회복하였고, 인앱결제 의무화와 가격 인상이 걸친 두 구간에 복합 구매에서 구독 중심으로 옮겨 갈 확률은 그 이전보다 ${f3(cHB.estimate)}(가구 군집 부트스트랩 95% 구간 ${f3(cHB.lo)}~${f3(cHB.hi)}) 높았다. 모형 없이 계산한 앱 내 아이템 구입의 지속률도 ${pc1(rman('inapp_item', RIV[0]).persist)}%에서 ${pc1(rman('inapp_item', RIV[1]).persist)}%, ${pc1(rman('inapp_item', RIV[2]).persist)}%로 낮아졌다가 ${pc1(rman('inapp_item', RIV[3]).persist)}%로 돌아왔다.`, { size: 20, line: 340 }),
  P(`그러나 이 변화를 가격 인상의 효과로 돌리기는 어렵다. 2022년에 인앱 가격이 오른 영상과 음원의 유료 이용은 줄지 않았고(음악 유료 이용의 지속률은 다섯 구간 내내 ${(100 * Math.min(...musicP)).toFixed(0)}~${(100 * Math.max(...musicP)).toFixed(0)}%), 줄어든 것은 종전부터 인앱결제 대상이던 앱 내 구매였다. 가격 인상에 더 많이 노출된 이용자가 구매를 더 많이 그만둔 것도 아니었다. 2021년은 앱 내 구매와 게임 이용이 일시적으로 높았던 해였으며, 2024년에는 조사의 측정이 달라진 흔적이 있어 영상 문항의 응답확률을 2024년 전후로 따로 추정하였다. 값이 오른 서비스의 이용이 이어졌다는 사실은 수수료 부담이 이용의 중단보다 지출의 증가로 이용자에게 돌아갔을 가능성을 가리킨다.`, { size: 20, line: 340 }),
  P(`분석 절차는 원자료에 적용하기 전에 모의자료로 검증하였다. 공표된 표본 크기(${comma(n.run.n_persons)}명)와 유지율에 맞춘 모의패널에서 절차는 상태의 수와 프로파일을 정확하게 복원하였고(응답확률 최대 오차 ${num(n.run.max_abs_err.theta, 3)}), 파이썬, R, LMest 패키지의 세 구현이 같은 해에 도달하였다. 전이확률이 0.06 달라지는 변화는 8,000명 표본에서 초점 검정으로 ${f3(mc(8000, 0.06).reject_rate_regime)}의 확률로만 검출되었으나, 원자료의 변화는 그보다 훨씬 커서 검정력은 제약이 되지 않았고 측정의 동등성이 제약이 되었다. 시기에 따른 전이의 차이는 규제의 인과효과가 아니며, 결제 경로를 관측하지 못한 점이 가장 큰 한계이다.`, { size: 20, line: 340 }),
  new Paragraph({ spacing: { before: 80, after: 60 }, children: [new TextRun({ text: '주제어: ', font: HEAD_FONT, size: 20, bold: true }), new TextRun({ text: '인앱결제 강제금지법, 앱마켓 규제, 한국미디어패널조사, 잠재전이분석, 부분 측정불변, 규제 강도, 플랫폼의 전략적 대응', font: BODY_FONT, size: 20 })] }),
  rule(),
];

const back = [
  h.H1('Abstract'),
  center('In-App Payment Regulation in Korea and Transitions in Digital Content Consumption States: A Latent Transition Analysis of the Korea Media Panel Microdata, 2020–2025', { size: 21, bold: true, after: 160, font: BODY_FONT }),
  P(`In 2021 Korea became the first jurisdiction to prohibit app-market operators from mandating a specific in-app payment system. Platforms responded by permitting third-party billing at a commission only four percentage points lower, in-app prices of major content services rose in 2022, and the regulator's first sanction was issued only in October 2026. This paper examines two propositions: that app-market-related firms' business and payment strategies changed around the regulation, and that platforms' strategic responses caused the regulation's actual effects to diverge from its policy goals. In firm-level data coded from press reports and official notices, 16 of 19 content services moved from in-app proprietary billing to platform billing, all 10 services with confirmed 2022 price changes raised in-app prices (median 15.4%), and only one adopted third-party billing; payment choice was secured in form only, while developer costs and consumer prices moved against the policy goals. On the user side, we analyse the individual microdata of the Korea Media Panel Survey for 2020–2025 (${comma(rr.n_persons)} persons in ${comma(rr.n_households)} households) with latent transition analysis on four indicators: paid app purchase, in-app item purchase, and paid use of video and of music. Three states are estimated (low consumption, subscription-centred, and multi-purchase). The probability of remaining in the multi-purchase state fell from ${f2(rA[0][2][2])} in 2020–21 to ${f2(rA[1][2][2])} in 2021–22 and ${f2(rA[2][2][2])} in 2022–23, then recovered to ${f2(rA[3][2][2])} and ${f2(rA[4][2][2])}; in the two intervals spanning the in-app payment mandate and the price increases, the probability of moving from the multi-purchase to the subscription-centred state was ${f3(cHB.estimate)} higher than before (household-cluster bootstrap 95% interval ${f3(cHB.lo)} to ${f3(cHB.hi)}). Model-free persistence of in-app item purchasing shows the same shape (${pc1(rman('inapp_item', RIV[0]).persist)}%, ${pc1(rman('inapp_item', RIV[1]).persist)}%, ${pc1(rman('inapp_item', RIV[2]).persist)}%, ${pc1(rman('inapp_item', RIV[3]).persist)}%). Yet the change cannot be attributed to the price increases: paid use of video and music, the services whose prices rose, did not decline; users more exposed to the price increases were no more likely to stop purchasing; 2021 was an exceptionally high year for in-app purchasing and gaming; and the survey measurement appears to have shifted in 2024, which we handle by letting the response probabilities of the video item differ from 2024 onward. Continued paid use of the services whose prices rose suggests that the commission burden reached users as higher spending rather than as exit. The procedure was validated beforehand on a synthetic panel, where it recovered the planted structure and three independent implementations agreed; the simulations warned of low power for small transition shifts, but in the microdata the binding problems were measurement comparability and common shocks, not power. Period differences in transitions are not causal effects of the regulation, and the survey does not observe the payment channel.`, { size: 20, line: 320, noIndent: true }),
  new Paragraph({ spacing: { before: 80 }, children: [new TextRun({ text: 'Keywords: ', font: BODY_FONT, size: 20, bold: true }), new TextRun({ text: 'in-app payment regulation, app markets, Korea Media Panel Survey, latent transition analysis, partial measurement invariance, strategic platform response', font: BODY_FONT, size: 20 })] }),
];

const p2 = require('./paper_part2')(h, FIG, n);
const body = [...front, ...require('./paper_part1')(h, FIG), ...p2.main, ...back, ...p2.appendix];

const doc = new Document({
  creator: 'Korea In-App LTA project', title: '한국 인앱결제 강제금지 규제와 디지털 콘텐츠 소비 상태의 전이',
  styles: { default: { document: { run: { font: BODY_FONT, size: 21 } } } },
  footnotes: h.FOOTNOTES,
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1417, bottom: 1417, left: 1417, right: 1417 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: BODY_FONT, size: 18 })] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, buf);
  console.log('written', OUT, buf.length, 'bytes');
});
