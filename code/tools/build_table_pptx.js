// build_table_pptx.js — 원자료 추정값 표를 파워포인트의 '표' 개체로 만든다(복사해서 다른 발표자료에 붙일 수 있게).
// 입력: outputs/real_parameter_table.csv (code/11_real_parameter_table.py)
// 출력: paper/실자료_추정값_표.pptx   (논문·요약 발표자료와는 별개의 파일)
const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');

const ROOT = path.resolve(__dirname, '..', '..');
const OUT = path.join(ROOT, 'paper', '실자료_추정값_표.pptx');
const lines = fs.readFileSync(path.join(ROOT, 'outputs', 'real_parameter_table.csv'), 'utf8').replace(/^﻿/, '').trim().split(/\r?\n/).slice(1).map((l) => l.split(','));

const NAVY = '1B2A41', INK = '1F2937', MUTED = '6B7280', LINE = 'D1D5DB', BAND = 'F3F6FA', ORANGE = 'EB6834', WHITE = 'FFFFFF';
const FONT = '맑은 고딕';
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
const s = pres.addSlide();
s.background = { color: WHITE };
s.addText('원자료에서 추정한 상태 비중, 응답확률, 전이확률', { x: 0.6, y: 0.3, w: 12.1, h: 0.55, fontSize: 24, bold: true, color: NAVY, margin: 0, isTextBox: true, fontFace: FONT });
s.addText('한국미디어패널 개인 원자료 2020~2025년, 11,362명 · 세 상태 모형(영상 문항만 2024년부터 따로 추정), 가중 추정', { x: 0.6, y: 0.85, w: 12.1, h: 0.35, fontSize: 12, color: MUTED, margin: 0, isTextBox: true, fontFace: FONT });

const cell = (text, o = {}) => ({ text, options: { fontFace: FONT, fontSize: 11.5, color: INK, valign: 'middle', ...o } });
const head = ['구분', '국면', 'S1 저소비', 'S2 구독 중심', 'S3 복합 구매'].map((t, i) => cell(t, { bold: true, color: WHITE, fill: { color: NAVY }, align: i < 2 ? 'left' : 'center' }));
const rows = [head];
let prev = null;
lines.forEach(([block, row, a, b, c]) => {
  const trans = block.startsWith('연간');
  const hike = row.startsWith('가격 인상기');
  const fill = hike ? { color: BAND } : { color: WHITE };
  const stayIdx = trans ? Number(block.match(/S(\d)/)[1]) - 1 : -1;        // 같은 상태에 머물 확률은 굵게
  const label = trans ? (block !== prev ? block : '') : (block === '상태 비중' ? row : `${block}: ${row}`);
  const regime = trans ? row : '';
  const top = block !== prev ? { type: 'solid', color: '9CA3AF', pt: 1 } : { type: 'none' };
  const border = [top, { type: 'none' }, { type: 'solid', color: LINE, pt: 0.5 }, { type: 'none' }];
  rows.push([
    cell(label, { fill, border }),
    cell(regime, { fill, border, color: hike ? ORANGE : MUTED, bold: hike }),
    ...[a, b, c].map((v, k) => cell(Number(v).toFixed(3), { fill, border, align: 'center', bold: k === stayIdx })),
  ]);
  prev = block;
});
s.addTable(rows, { x: 0.6, y: 1.35, w: 12.1, colW: [3.9, 2.9, 1.75, 1.8, 1.75], rowH: 0.33, margin: [0, 0.1, 0, 0.1] });   // 칸 안쪽 여백(인치)
s.addText('전이확률은 국면에 속한 구간의 평균, 굵은 숫자는 같은 상태에 머물 확률. 2020년 조사에는 영상의 지불 유형 문항이 없다. 시기에 따른 차이는 규제의 인과효과가 아니다.',
  { x: 0.6, y: 6.95, w: 12.1, h: 0.35, fontSize: 10, color: MUTED, margin: 0, isTextBox: true, fontFace: FONT });

// ── 둘째 쪽: 복합 구매 상태에서 출발하는 구간별 전이확률(추정값과 95% 구간) ──
// 입력: outputs/real_s3_transition_table.csv (code/13_real_s3_transition_table.py)
const s3 = fs.readFileSync(path.join(ROOT, 'outputs', 'real_s3_transition_table.csv'), 'utf8').replace(/^﻿/, '').trim().split(/\r?\n/).slice(1).map((l) => l.split(','));
const s2 = pres.addSlide();
s2.background = { color: WHITE };
s2.addText('복합 구매 상태에서 출발하는 연간 전이확률', { x: 0.6, y: 0.3, w: 12.1, h: 0.55, fontSize: 24, bold: true, color: NAVY, margin: 0, isTextBox: true, fontFace: FONT });
s2.addText('한국미디어패널 개인 원자료 2020~2025년, 11,362명 · 실제 추정값, 95% 구간은 가구 군집 부트스트랩', { x: 0.6, y: 0.85, w: 12.1, h: 0.35, fontSize: 12, color: MUTED, margin: 0, isTextBox: true, fontFace: FONT });
const HIKE = new Set(['2021→2022', '2022→2023']);
const rows2 = [['구간', '도착 상태', '추정값', '95% 구간'].map((t, i) => cell(t, { bold: true, color: WHITE, fill: { color: NAVY }, align: i < 2 ? 'left' : 'center' }))];
let prevIv = null;
s3.forEach(([iv, dest, est, lo, hi]) => {
  const hike = HIKE.has(iv);
  const fill = hike ? { color: BAND } : { color: WHITE };
  const top = iv !== prevIv ? { type: 'solid', color: '9CA3AF', pt: 1 } : { type: 'none' };
  const border = [top, { type: 'none' }, { type: 'solid', color: LINE, pt: 0.5 }, { type: 'none' }];
  const stay = dest.startsWith('S3');
  rows2.push([
    cell(iv !== prevIv ? iv.replace('→', ' → ') : '', { fill, border, color: hike ? ORANGE : INK, bold: hike }),
    cell(dest, { fill, border }),
    cell(Number(est).toFixed(3), { fill, border, align: 'center', bold: stay }),
    cell(`${Number(lo).toFixed(3)} ~ ${Number(hi).toFixed(3)}`, { fill, border, align: 'center' }),
  ]);
  prevIv = iv;
});
s2.addTable(rows2, { x: 0.6, y: 1.35, w: 12.1, colW: [3.0, 3.6, 2.5, 3.0], rowH: 0.33, margin: [0, 0.1, 0, 0.1] });
s2.addText('굵은 숫자는 복합 구매 상태에 머물 확률. 주황색 구간은 인앱결제 의무화와 가격 인상이 걸친 구간. 원자료이므로 참값은 없다. 시기에 따른 차이는 규제의 인과효과가 아니다.',
  { x: 0.6, y: 6.95, w: 12.1, h: 0.35, fontSize: 10, color: MUTED, margin: 0, isTextBox: true, fontFace: FONT });
pres.writeFile({ fileName: OUT }).then(() => console.log('written', OUT));
