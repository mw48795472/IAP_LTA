// docx_helpers.js — 논문 워드 파일을 만들 때 쓰는 공통 양식(문단·표·그림) 함수
const fs = require('fs');
const {
  Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, AlignmentType, BorderStyle,
  WidthType, ShadingType, VerticalAlign, FootnoteReferenceRun,
} = require('docx');

const BODY_FONT = { ascii: 'Times New Roman', hAnsi: 'Times New Roman', eastAsia: '바탕', cs: 'Times New Roman' };
const HEAD_FONT = { ascii: 'Arial', hAnsi: 'Arial', eastAsia: '맑은 고딕', cs: 'Arial' };
const CONTENT_W = 9070;            // A4, 좌우 여백 2.5cm 기준 본문 폭(DXA)
const INK2 = '555555';

// 각주: 본문에 ⟦각주 내용⟧ 이라고 쓰면 그 자리에 각주 번호가 붙고 내용은 쪽 아래로 간다(번호는 워드가 순서대로 매긴다).
const FOOTNOTES = {};
let footnoteCount = 0;

// "**굵게**", "__기울임__", "^^위첨자^^", ",,아래첨자,,", "⟦각주⟧" 표기를 TextRun 배열로 바꾼다.
function runs(text, opt = {}) {
  const out = [];
  const re = /(⟦.+?⟧|\*\*.+?\*\*|__.+?__|\^\^.+?\^\^|,,.+?,,)/g;
  String(text).split(re).filter((s) => s !== '').forEach((part) => {
    const base = { font: opt.font || BODY_FONT, size: opt.size || 21, color: opt.color };
    if (part.startsWith('⟦') && part.endsWith('⟧')) {
      footnoteCount += 1;
      FOOTNOTES[footnoteCount] = { children: [new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: 276, after: 40 }, children: runs(` ${part.slice(1, -1)}`, { size: 18 }) })] };
      out.push(new FootnoteReferenceRun(footnoteCount));
      return;
    }
    if (part.startsWith('**') && part.endsWith('**')) out.push(new TextRun({ ...base, text: part.slice(2, -2), bold: true }));
    else if (part.startsWith('__') && part.endsWith('__')) out.push(new TextRun({ ...base, text: part.slice(2, -2), italics: true }));
    else if (part.startsWith('^^') && part.endsWith('^^')) out.push(new TextRun({ ...base, text: part.slice(2, -2), superScript: true }));
    else if (part.startsWith(',,') && part.endsWith(',,')) out.push(new TextRun({ ...base, text: part.slice(2, -2), subScript: true }));
    else out.push(new TextRun({ ...base, text: part, bold: opt.bold, italics: opt.italics }));
  });
  return out;
}

// 본문 문단(양쪽 맞춤, 첫 줄 들여쓰기)
function P(text, opt = {}) {
  return new Paragraph({
    alignment: opt.align || AlignmentType.JUSTIFIED,
    indent: opt.noIndent ? undefined : { firstLine: 220 },
    spacing: { line: opt.line || 372, after: opt.after === undefined ? 100 : opt.after, before: opt.before || 0 },
    keepNext: opt.keepNext,
    children: runs(text, opt),
  });
}

function H1(text) {      // 장 제목: Ⅰ. 서론
  return new Paragraph({
    spacing: { before: 420, after: 200 }, keepNext: true, alignment: AlignmentType.LEFT,
    children: [new TextRun({ text, font: HEAD_FONT, size: 28, bold: true })],
  });
}
function H2(text) {      // 절 제목: 1. 문제 제기
  return new Paragraph({
    spacing: { before: 280, after: 120 }, keepNext: true,
    children: [new TextRun({ text, font: HEAD_FONT, size: 23, bold: true })],
  });
}
function H3(text) {
  return new Paragraph({
    spacing: { before: 200, after: 80 }, keepNext: true,
    children: [new TextRun({ text, font: HEAD_FONT, size: 21, bold: true })],
  });
}

// 표: 학술지식 3선 표(위·아래 굵은 선, 머리글 아래 가는 선)
function T(caption, headers, rows, widths, opt = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const scale = CONTENT_W / total;
  const w = widths.map((x) => Math.round(x * scale));
  w[w.length - 1] += CONTENT_W - w.reduce((a, b) => a + b, 0);
  const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
  const thick = { style: BorderStyle.SINGLE, size: 12, color: '000000' };
  const thin = { style: BorderStyle.SINGLE, size: 4, color: '000000' };
  const hair = { style: BorderStyle.SINGLE, size: 2, color: 'BBBBBB' };
  const size = opt.size || 18;
  const aligns = opt.align || headers.map((_, i) => (i === 0 ? 'left' : 'center'));
  const cell = (txt, i, isHead, isLast, bandTop) => new TableCell({   // keepNext: 표가 쪽 사이에서 갈라지지 않게 한다
    width: { size: w[i], type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    shading: isHead ? { type: ShadingType.CLEAR, fill: 'F2F2F2', color: 'auto' } : undefined,
    borders: {
      top: isHead ? thick : (bandTop ? hair : none), bottom: isHead ? thin : (isLast ? thick : none),
      left: none, right: none,
    },
    children: String(txt).split('\n').map((line) => new Paragraph({
      alignment: isHead ? AlignmentType.CENTER : ({ left: AlignmentType.LEFT, center: AlignmentType.CENTER, right: AlignmentType.RIGHT }[aligns[i]]),
      spacing: { line: 260, after: 0 }, keepNext: !isLast,
      children: runs(line, { font: HEAD_FONT, size, bold: isHead }),
    })),
  });
  const table = new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: w, alignment: AlignmentType.CENTER,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => cell(h, i, true, false)) }),
      ...rows.map((r, ri) => new TableRow({
        cantSplit: true,
        children: r.map((c, i) => cell(c, i, false, ri === rows.length - 1, opt.rules && ri > 0)),
      })),
    ],
  });
  const out = [
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 240, after: 90 }, keepNext: true,
      children: runs(caption, { font: HEAD_FONT, size: 19, bold: true }),
    }),
    table,
  ];
  (opt.notes || []).forEach((n, i) => out.push(new Paragraph({
    spacing: { before: i === 0 ? 70 : 0, after: 0, line: 250 },
    children: runs(n, { font: HEAD_FONT, size: 16, color: INK2 }),
  })));
  out.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
  return out;
}

// PNG 크기 읽기(IHDR)
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), data: b };
}

// 그림: 본문 폭에 맞춰 넣고 아래에 캡션
function F(file, caption, opt = {}) {
  const { w, h, data } = pngSize(file);
  const width = opt.width || 600;                 // 픽셀(96dpi) — 600px ≈ 15.9cm
  const out = [
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 200, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: 'png', data, transformation: { width, height: Math.round(width * h / w) } })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: opt.notes ? 40 : 200 }, keepLines: true,
      children: runs(caption, { font: HEAD_FONT, size: 19, bold: true }),
    }),
  ];
  (opt.notes || []).forEach((n, i, a) => out.push(new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: i === a.length - 1 ? 200 : 0, line: 250 },
    children: runs(n, { font: HEAD_FONT, size: 16, color: INK2 }),
  })));
  return out;
}

// 참고문헌(내어쓰기)
function Ref(text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED, indent: { left: 440, hanging: 440 }, spacing: { line: 320, after: 60 },
    children: runs(text, { size: 19 }),
  });
}

// 수식 줄(가운데)
function Eq(text, label) {
  return new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 120, after: 160, line: 372 },
    children: [...runs(text, { font: { ascii: 'Cambria Math', hAnsi: 'Cambria Math', eastAsia: '바탕' }, size: 21 }),
      ...(label ? [new TextRun({ text: `      ${label}`, font: BODY_FONT, size: 21 })] : [])],
  });
}

const num = (x, d = 3) => Number(x).toFixed(d);
const pct = (x, d = 1) => `${(100 * Number(x)).toFixed(d)}`;
const comma = (x, d = 0) => Number(x).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

module.exports = { runs, P, H1, H2, H3, T, F, Ref, Eq, num, pct, comma, BODY_FONT, HEAD_FONT, CONTENT_W, INK2, FOOTNOTES };
