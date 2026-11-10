// paper_part3.js — 논문 Ⅴ장: 한국미디어패널 개인 원자료(2020~2025)의 잠재전이분석.
// 수치는 outputs/real_summary.json 과 outputs/real_*.csv 에서 읽는다(code/07, 08 스크립트가 만든다).
const fs = require('fs');
const path = require('path');

module.exports = function part3(h, FIG) {
  const { P, H1, H2, T, F, num, comma } = h;
  const OUT = path.join(__dirname, '..', '..', 'outputs');
  const rs = JSON.parse(fs.readFileSync(path.join(OUT, 'real_summary.json'), 'utf8'));
  const csv = (name) => {
    const lines = fs.readFileSync(path.join(OUT, name), 'utf8').replace(/^﻿/, '').trim().split(/\r?\n/);
    const head = lines[0].split(',');
    return lines.slice(1).map((l) => { const v = l.split(','); const o = {}; head.forEach((k, i) => { o[k] = v[i]; }); return o; });
  };
  const c = [];
  const neg = (s) => String(s).replace('-', '−');
  const f1 = (x) => num(x, 1), f2 = (x) => num(x, 2), f3 = (x) => neg(num(x, 3));
  const p1 = (x) => (100 * Number(x)).toFixed(1);
  const p0 = (x) => (100 * Number(x)).toFixed(0);
  const ci3 = (lo, hi) => `${f3(lo)}~${f3(hi)}`;
  const WAVES = rs.waves;
  const IV = WAVES.slice(0, -1).map((a, i) => `${a}→${WAVES[i + 1]}`);
  const SL = ['S1 저소비', 'S2 구독 중심', 'S3 복합 구매'];
  const prev = (y) => rs.prevalence.find((r) => Number(r.wave) === y);
  const na = (v, d = 1) => (v === null || v === undefined || Number.isNaN(Number(v)) ? '–' : num(v, d));
  const man = (item, iv) => rs.manifest.find((r) => r.item === item && r.interval === iv);
  const occ = csv('real_state_occupancy.csv');
  const occAt = (y, k) => occ.find((r) => Number(r.wave) === y && r.state === SL[k]);
  const tr = csv('real_transition_probabilities.csv');
  const trAt = (iv, a, b) => tr.find((r) => r.interval === iv && r.from_state === SL[a] && r.to_state === SL[b]);
  const prof = csv('real_response_profiles.csv');
  const profAt = (item, k, period) => prof.find((r) => r.item === item && r.state === SL[k] && (period ? r.period === period : true));
  const con = (t, cname) => rs.contrasts.find((r) => r.transition === t && r.contrast === cname);
  const test = (prefix) => rs.tests.find((r) => r.test.startsWith(prefix));
  const sel = (K, m) => rs.model_selection.find((r) => r.K === K && r.measurement === m);
  const INV = '완전 측정불변', BRK = '영상 문항 2024년 단절';
  const pv = (p) => (Number(p) < 0.001 ? '< 0.001' : num(p, 3));
  const m = rs.main;
  const mi = (j, iv) => man(j, iv);
  const persist = (j) => IV.map((iv) => mi(j, iv)).filter(Boolean).map((r) => r.persist);

  c.push(H1('Ⅴ. 원자료의 잠재전이분석'));
  c.push(H2('1. 패널의 구성과 지표의 추이'));
  c.push(P(`이 장은 한국미디어패널 개인 원자료 2020~2025년에 Ⅲ장의 분석 틀을 적용한다. 여섯 해에 한 번이라도 응답한 개인은 ${comma(rs.n_persons)}명(${comma(rs.n_households)}가구), 개인×연도 관측은 ${comma(rs.n_person_waves)}건이고, 여섯 해에 모두 응답한 사람은 ${comma(rs.n_all_waves)}명이다. 연도별 응답자 수와 전년 대비 유지율은 <표 7>의 공표값과 같았다. 변수는 각 문항의 가중 비율이 보고서의 공표 경험률과 소수 첫째 자리까지 일치하는지로 확인하였다. 2021~2025년의 유료 애플리케이션 구입, 앱 내 아이템 구입, 월정액 가입, 온라인 음악 이용이 모두 일치하였다(outputs/real_variable_map.csv, real_prevalence_by_wave.csv).`));
  c.push(P(`원자료는 집계치로 할 수 없던 두 가지를 가능하게 한다. 하나는 지표를 <표 3>의 정의대로 만드는 것이다. 월평균 지출액이 있으므로 영상과 음악은 지출이 양수인 경우만 유료 이용으로 두었다. 이렇게 정의한 음악 유료 이용률은 ${f1(prev(2025).paid_music)}%로, 무료 이용을 포함한 이용률 ${f1(prev(2025).pub_music_use)}%의 절반 수준이다(2025년). 다른 하나는 2020년 조사를 더하는 것이다. 다만 2020년 조사에는 동영상 서비스의 지불 유형 문항이 없어 영상 지표는 2021년부터 관측된다.`));
  c.push(...T('<표 24> 원자료로 계산한 지표의 연도별 가중 비율(전체 응답자 대비 %)', ['구분', ...WAVES.map(String)], [
    ['개인 응답자 수(명)', ...WAVES.map((y) => comma(prev(y).respondents))],
    ['유료 앱 구입', ...WAVES.map((y) => na(prev(y).paid_app))],
    ['앱 내 아이템 구입', ...WAVES.map((y) => na(prev(y).inapp_item))],
    ['영상 유료 이용(지출 양수)', ...WAVES.map((y) => na(prev(y).paid_video))],
    ['음악 유료 이용(지출 양수)', ...WAVES.map((y) => na(prev(y).paid_music))],
    ['참고: 웹툰·전자책 유료 이용', ...WAVES.map((y) => na(prev(y).paid_webtoon))],
    ['참고: 온라인 게임 이용', ...WAVES.map((y) => na(prev(y).use_game))],
    ['참고: 음악 이용자 중 지출이 있는 비율', ...WAVES.map((y) => na(prev(y).music_spend_positive_share))],
    ['참고: 웹툰·전자책 이용자 중 지출이 있는 비율', ...WAVES.map((y) => na(prev(y).webtoon_spend_positive_share))],
  ], [3070, 1000, 1000, 1000, 1000, 1000, 1000], { align: ['left', 'center', 'center', 'center', 'center', 'center', 'center'], size: 17, notes: ['자료: 한국미디어패널 개인 원자료(정보통신정책연구원), 연도별 횡단 가중치 적용. 위 네 줄이 잠재전이분석의 지표이다. 스마트 기기 비이용자와 동영상 서비스 비이용자는 0으로 두었다. 영상 지표는 2020년 조사에 문항이 없다.'] }));
  c.push(P(`<표 24>에서 세 가지가 눈에 띈다. 첫째, 2020년을 더하면 2021년이 예외적으로 높은 해였음이 드러난다. 앱 내 아이템 구입은 2020년 ${f1(prev(2020).inapp_item)}%에서 2021년 ${f1(prev(2021).inapp_item)}%로 뛰었다가 2022년 ${f1(prev(2022).inapp_item)}%로 돌아왔고, 온라인 게임 이용도 ${f1(prev(2020).use_game)}%, ${f1(prev(2021).use_game)}%, ${f1(prev(2022).use_game)}%로 같은 모양이다. Ⅳ장 9절에서 2021년을 기준으로 본 하락의 상당 부분은 2021년의 일시적 상승이 되돌아간 것이다. 둘째, 그렇더라도 2023년의 앱 내 아이템 구입(${f1(prev(2023).inapp_item)}%)은 2020년 수준보다 낮다. 셋째, 2024년에는 여러 지표가 한꺼번에 달라졌다. 음악 이용자 가운데 지출이 있다고 답한 비율이 2023년 ${f1(prev(2023).music_spend_positive_share)}%에서 2024년 ${f1(prev(2024).music_spend_positive_share)}%로, 웹툰·전자책에서는 ${f1(prev(2023).webtoon_spend_positive_share)}%에서 ${f1(prev(2024).webtoon_spend_positive_share)}%로 올랐고, 영상 유료 이용은 ${f1(prev(2023).paid_video)}%에서 ${f1(prev(2024).paid_video)}%가 되었다. 이용 행태가 한 해에 이만큼 달라졌다고 보기는 어려워, 2024년에 조사의 측정이 달라졌을 가능성을 모형에 반영하였다(3절).`));

  c.push(H2('2. 관측 지표의 전이율'));
  c.push(P('잠재상태를 추정하기 전에, 같은 사람의 응답을 두 해씩 이어 붙여 지표 수준의 전이율을 계산하였다. 어느 해에 구입한 사람이 다음 해에도 구입한 비율(지속)과, 구입하지 않은 사람이 다음 해에 구입한 비율(진입)이다. 이 계산에는 모형의 가정이 들어가지 않는다. 구간추정은 가구를 단위로 재표집한 부트스트랩으로 하였다.'));
  const mrow = (item, label) => IV.map((iv) => man(item, iv)).filter(Boolean).map((r, i) => [i === 0 ? label : '', r.interval, comma(r.n_buyers),
    `${p1(r.persist)} (${p1(r.persist_lo)}~${p1(r.persist_hi)})`, `${p1(r.entry)} (${p1(r.entry_lo)}~${p1(r.entry_hi)})`]);
  c.push(...T('<표 25> 관측 지표의 연간 전이율(가중, %)', ['지표', '구간', '앞 해의 구입자(명)', '지속: 구입자가 다음 해에도 구입', '진입: 비구입자가 다음 해에 구입'], [
    ...mrow('inapp_item', '앱 내 아이템 구입'), ...mrow('paid_app', '유료 앱 구입'), ...mrow('paid_music', '음악 유료 이용'), ...mrow('paid_video', '영상 유료 이용'),
  ], [1900, 1300, 1500, 2300, 2070], { align: ['left', 'center', 'center', 'center', 'center'], size: 17, notes: ['주: 두 해에 모두 응답한 사람. 앞 해의 횡단 가중치 적용. 괄호 안은 가구 군집 부트스트랩 95% 구간. 구입자 수는 가중하지 않은 인원.'] }));
  c.push(P(`<표 25>의 결과는 분명하다. 앱 내 아이템을 구입한 사람이 다음 해에도 구입한 비율은 2020→2021년 ${p1(mi('inapp_item', IV[0]).persist)}%에서 2021→2022년 ${p1(mi('inapp_item', IV[1]).persist)}%, 2022→2023년 ${p1(mi('inapp_item', IV[2]).persist)}%로 낮아졌다가 2023→2024년 ${p1(mi('inapp_item', IV[3]).persist)}%, 2024→2025년 ${p1(mi('inapp_item', IV[4]).persist)}%로 회복하였다. 새로 구입하기 시작한 비율도 ${p1(mi('inapp_item', IV[0]).entry)}%에서 ${p1(mi('inapp_item', IV[1]).entry)}%, ${p1(mi('inapp_item', IV[2]).entry)}%로 줄었다가 ${p1(mi('inapp_item', IV[3]).entry)}%로 돌아왔다. 인앱결제 의무화와 가격 인상이 회상 기간에 들어가는 두 구간에서 앱 내 구매는 덜 이어지고 덜 시작되었다. 유료 앱 구입도 같은 방향이나 폭이 작다.`));
  c.push(P(`그런데 음악 유료 이용의 지속률은 다섯 구간 모두 ${p0(Math.min(...persist('paid_music')))}~${p0(Math.max(...persist('paid_music')))}% 범위에 머물렀고, 영상 유료 이용의 지속률은 ${p1(mi('paid_video', IV[1]).persist)}%에서 ${p1(mi('paid_video', IV[4]).persist)}%로 계속 올랐다. 2022년에 인앱 가격이 오른 것은 영상과 음원, 웹툰 서비스였는데(Ⅳ장 8절), 바로 그 서비스의 유료 이용은 이 시기에 줄지 않았다. 줄어든 것은 게임 아이템과 이모티콘처럼 종전부터 인앱결제 대상이던 앱 내 구매이다. 이 차이는 뒤의 해석에서 중요하다.`));

  c.push(H2('3. 상태 수와 측정불변성'));
  c.push(...T('<표 26> 상태 수와 측정 사양에 따른 적합도', ['상태 수', 'BIC: 완전 측정불변', 'BIC: 영상 문항만 2024년 단절', '모수 수(단절)', '최소 상태 비중(단절)', '같은 해에 도달한 초기값 수(단절)'],
    [1, 2, 3, 4, 5].map((K) => [String(K), comma(sel(K, INV).bic, 1), comma(sel(K, BRK).bic, 1), String(sel(K, BRK).npar), f3(sel(K, BRK).min_state_share), `${sel(K, BRK).n_replicated}/${sel(K, BRK).n_starts}`]),
    [900, 1800, 2300, 1200, 1500, 1370], { size: 17, notes: ['주: 가중 추정(처음 응답한 해의 횡단 가중치, 평균 1로 정규화), 구간별 자유 전이. BIC의 표본 크기는 가중치의 합(개인 수)이다.'] }));
  c.push(P(`모의자료와 달리 BIC는 상태 수가 늘수록 계속 낮아졌고 다섯 상태까지 바닥을 보이지 않았다(<표 26>). 1만 명이 넘는 실제 자료에서 흔한 일이며, 상태가 모의자료처럼 뚜렷이 나뉘지 않음을 뜻한다. 본 연구는 세 상태를 주 모형으로 삼았다. 세 상태의 해는 모든 초기값에서 재현되었고 Ⅲ장에서 미리 정한 저소비, 구독 중심, 복합 구매의 구분과 대응하며, 넷 이상에서는 가장 작은 상태가 표본의 ${p0(sel(4, BRK).min_state_share)}% 안팎으로 줄어든다. 네 상태 모형은 민감도 분석으로 함께 제시한다(6절). 상태 수의 선택에 판단이 들어갔다는 점은 한계이다.`));
  const invRow = (name) => rs.measurement_invariance.find((r) => r.measurement === name);
  c.push(P(`측정불변성은 성립하지 않았다. 세 상태 모형에서 응답확률을 모든 시점에 같게 둔 사양의 BIC는 ${comma(invRow('완전 측정불변').bic, 1)}인데, 영상 문항의 응답확률만 2024년부터 따로 두면 ${comma(invRow('영상 문항만 2024년 단절').bic, 1)}로 크게 낮아진다. 음악 문항까지 풀면 ${comma(invRow('영상·음악 문항 2024년 단절').bic, 1)}, 네 문항을 모두 풀면 ${comma(invRow('네 문항 모두 2024년 단절').bic, 1)}, 시점마다 자유롭게 두면 ${comma(invRow('시점별 자유').bic, 1)}이다. 풀수록 적합도는 좋아지지만, 네 문항을 모두 풀면 2024년 전후의 상태가 같은 상태라는 보장이 사라져 전이확률을 해석할 수 없게 된다. 그래서 주 모형은 개선 폭이 가장 큰 영상 문항만 풀고 나머지 세 문항으로 상태의 뜻을 고정하였다. 이 사양은 2024년 영상 지표의 수준 변화를 상태 이동이 아닌 측정의 변화로 읽는다. 반대로 읽는 완전 측정불변 사양의 결과도 6절에 제시한다.`));

  c.push(H2('4. 상태 프로파일과 상태 비중'));
  const pcell = (item, k, period) => { const r = profAt(item, k, period); return `${f3(r.estimate)}\n(${ci3(r.lo, r.hi)})`; };
  const ocell = (y, k) => { const r = occAt(y, k); return `${f3(r.estimate)}\n(${ci3(r.lo, r.hi)})`; };
  c.push(...T('<표 27> 주 모형의 상태별 응답확률과 연도별 상태 비중', ['구분', ...SL], [
    ['응답확률: 유료 앱 구입', ...[0, 1, 2].map((k) => pcell('paid_app', k))],
    ['응답확률: 앱 내 아이템 구입', ...[0, 1, 2].map((k) => pcell('inapp_item', k))],
    ['응답확률: 영상 유료 이용(2021~2023년)', ...[0, 1, 2].map((k) => pcell('paid_video', k, '2020~2023'))],
    ['응답확률: 영상 유료 이용(2024~2025년)', ...[0, 1, 2].map((k) => pcell('paid_video', k, '2024~2025'))],
    ['응답확률: 음악 유료 이용', ...[0, 1, 2].map((k) => pcell('paid_music', k))],
    ...WAVES.map((y) => [`상태 비중: ${y}년`, ...[0, 1, 2].map((k) => ocell(y, k))]),
  ], [3400, 1890, 1890, 1890], { size: 17, notes: [`주: 세 상태, 영상 문항만 2024년부터 응답확률을 따로 둔 부분 측정불변, 구간별 자유 전이, 가중 추정. 괄호 안은 가구 군집 부트스트랩 95% 구간(${rs.bootstrap.n_valid}회).`] }));
  c.push(...F(`${FIG}/fig12_real_states.png`, '<그림 12> 원자료에서 추정한 상태별 응답확률(가)과 상태 비중의 추이(나)', { width: 600, notes: ['주: <표 27>과 같은 모형. 음영은 2022·2023년 조사.'] }));
  c.push(P(`세 상태의 프로파일은 Ⅲ장에서 예상한 구분과 맞았다(<표 27>, <그림 12>). 저소비 상태는 네 지표의 확률이 모두 0.03 아래이다. 구독 중심 상태는 영상 유료 이용 확률이 ${f2(profAt('paid_video', 1, '2020~2023').estimate)}, 음악이 ${f2(profAt('paid_music', 1).estimate)}이고 앱 구매는 거의 하지 않는다. 복합 구매 상태는 앱 내 아이템 구입 확률이 ${f2(profAt('inapp_item', 2).estimate)}, 유료 앱 구입이 ${f2(profAt('paid_app', 2).estimate)}이며 영상(${f2(profAt('paid_video', 2, '2020~2023').estimate)})과 음악(${f2(profAt('paid_music', 2).estimate)})도 함께 이용한다. 2024년부터 영상의 응답확률은 구독 중심 ${f2(profAt('paid_video', 1, '2024~2025').estimate)}, 복합 구매 ${f2(profAt('paid_video', 2, '2024~2025').estimate)}로 높아진다.`));
  c.push(P(`상태 비중의 변화는 두 흐름으로 나뉜다. 저소비 상태는 2020년 ${p1(occAt(2020, 0).estimate)}%에서 2025년 ${p1(occAt(2025, 0).estimate)}%로 줄고 구독 중심 상태가 그만큼 늘었다. 영상 구독의 확산이다. 복합 구매 상태는 이와 달리 오르내렸다. 2020년 ${p1(occAt(2020, 2).estimate)}%에서 2021년 ${p1(occAt(2021, 2).estimate)}%로 늘었다가 2022년 ${p1(occAt(2022, 2).estimate)}%, 2023년 ${p1(occAt(2023, 2).estimate)}%로 줄었고, 2024년에 ${p1(occAt(2024, 2).estimate)}%로 다시 늘었다. 평균 최대 사후확률은 ${f3(m.classification.avepp !== undefined ? m.classification.avepp : (m.classification.mean_max_posterior || 0))}이다.`));

  c.push(H2('5. 전이확률과 국면 간 차이'));
  const tcell = (iv, a, b) => { const r = trAt(iv, a, b); return `${f3(r.estimate)}\n(${ci3(r.lo, r.hi)})`; };
  c.push(...T('<표 28> 복합 구매 상태와 구독 중심 상태에서 출발하는 연간 전이확률', ['구간', '복합 구매\n→ 저소비', '복합 구매\n→ 구독 중심', '복합 구매\n유지', '구독 중심\n→ 저소비', '구독 중심\n유지', '구독 중심\n→ 복합 구매'],
    IV.map((iv) => [iv, tcell(iv, 2, 0), tcell(iv, 2, 1), tcell(iv, 2, 2), tcell(iv, 1, 0), tcell(iv, 1, 1), tcell(iv, 1, 2)]),
    [1270, 1300, 1300, 1300, 1300, 1300, 1300], { size: 16, notes: ['주: <표 27>과 같은 모형. 괄호 안은 가구 군집 부트스트랩 95% 구간.'] }));
  c.push(...F(`${FIG}/fig13_real_transitions.png`, '<그림 13> 복합 구매 상태에서의 전이확률(가)과 앱 내 아이템 구입의 관측 전이율(나)', { width: 600, notes: ['주: (가)는 주 모형의 추정값, (나)는 <표 25>의 관측값. 띠는 가구 군집 부트스트랩 95% 구간. 음영은 2021→2022년, 2022→2023년 구간.'] }));
  c.push(...F(`${FIG}/fig14_real_transition_matrices.png`, '<그림 14> 원자료에서 추정한 구간별 전이행렬', { width: 600, notes: ['주: <표 27>과 같은 모형. 칸의 값은 출발 상태(행)에서 도착 상태(열)로의 연간 전이확률, 괄호 안은 가구 군집 부트스트랩 95% 구간. 모의자료의 <그림 6>에 대응하는 실제 추정치이다.'] }));
  const cHB = con('복합 구매 → 구독 중심', '가격 인상기 − 이전'), cHA = con('복합 구매 → 구독 중심', '가격 인상기 − 이후');
  const sHB = con('복합 구매 유지', '가격 인상기 − 이전'), uHB = con('구독 중심 → 복합 구매', '가격 인상기 − 이전'), dS1 = con('복합 구매 → 저소비', '가격 인상기 − 이전');
  c.push(P(`복합 구매 상태에 머물 확률은 2020→2021년 ${f2(trAt(IV[0], 2, 2).estimate)}에서 2021→2022년 ${f2(trAt(IV[1], 2, 2).estimate)}, 2022→2023년 ${f2(trAt(IV[2], 2, 2).estimate)}로 낮아졌다가 2023→2024년 ${f2(trAt(IV[3], 2, 2).estimate)}, 2024→2025년 ${f2(trAt(IV[4], 2, 2).estimate)}가 되었다(<표 28>, <그림 13>). 세 상태 사이의 전이확률 전체는 <그림 14>에 있다. 이 상태를 떠난 사람은 대부분 구독 중심 상태로 갔다. 복합 구매에서 구독 중심으로 옮겨 갈 확률은 차례로 ${f2(trAt(IV[0], 2, 1).estimate)}, ${f2(trAt(IV[1], 2, 1).estimate)}, ${f2(trAt(IV[2], 2, 1).estimate)}, ${f2(trAt(IV[3], 2, 1).estimate)}, ${f2(trAt(IV[4], 2, 1).estimate)}이다. 저소비 상태로 곧장 내려간 사람은 어느 구간에서나 열 명에 한 명이 되지 않았다. 앱 구매를 그만둔 사람이 영상과 음악의 구독까지 끊지는 않았다는 뜻이다.`));
  c.push(...T('<표 29> 국면 간 전이확률의 차이', ['전이', '가격 인상기 − 이전', '가격 인상기 − 이후'],
    ['복합 구매 → 구독 중심', '복합 구매 → 저소비', '복합 구매 유지', '구독 중심 → 복합 구매', '구독 중심 → 저소비', '저소비 → 구독 중심'].map((t) => {
      const a = con(t, '가격 인상기 − 이전'), b = con(t, '가격 인상기 − 이후');
      return [t, `${f3(a.estimate)} (${ci3(a.lo, a.hi)})`, `${f3(b.estimate)} (${ci3(b.lo, b.hi)})`];
    }), [3070, 3000, 3000], { align: ['left', 'center', 'center'], size: 17, notes: ['주: 이전은 2020→2021년, 가격 인상기는 2021→2022년과 2022→2023년의 평균, 이후는 2023→2024년과 2024→2025년의 평균. 괄호 안은 가구 군집 부트스트랩 95% 구간. 국면의 구분은 정책 연표에 따른 것이나 세 국면으로 나눈 것은 자료를 본 뒤의 결정이다.'] }));
  const tO = test('총괄'), tP = test('초점: 동질 대 두 국면 [0,0,1,1,1]'), tE = test('초점: 동질 대 두 국면 [0,1,1,1,1]'), t3 = test('초점: 동질 대 세 국면'), tR = test('잔여: 세 국면');
  c.push(P(`국면 사이의 차이는 구간추정으로 확인된다(<표 29>). 복합 구매에서 구독 중심으로 옮겨 갈 확률은 가격 인상기에 그 이전보다 ${f3(cHB.estimate)}(95% 구간 ${ci3(cHB.lo, cHB.hi)}), 이후보다 ${f3(cHA.estimate)}(${ci3(cHA.lo, cHA.hi)}) 높았다. 복합 구매 상태에 머물 확률은 이전보다 ${f3(Math.abs(sHB.estimate))} 낮았고(${ci3(sHB.lo, sHB.hi)}), 구독 중심에서 복합 구매로 올라갈 확률도 ${f3(Math.abs(uHB.estimate))} 낮았다(${ci3(uHB.lo, uHB.hi)}). 복합 구매에서 저소비로 내려가는 확률의 차이는 ${f3(dS1.estimate)}(${ci3(dS1.lo, dS1.hi)})로 0과 구별되지 않았다. 비가중 적합의 우도비 검정에서 전이가 모든 구간에서 같다는 가설은 기각되었다(총괄 검정 ${comma(tO.stat, 1)}, 자유도 ${tO.df}, __p__ ${pv(tO.p)}). Ⅲ장에서 미리 정한 두 국면 사양의 초점 검정은 ${comma(tP.stat, 1)}(자유도 ${tP.df}), 경계를 한 구간 앞당긴 사양은 ${comma(tE.stat, 1)}, 세 국면 사양은 ${comma(t3.stat, 1)}(자유도 ${t3.df})이었고 모두 __p__ < 0.001이다. 경계를 2021→2022년 구간부터로 잡은 쪽이 미리 정한 사양보다 자료에 잘 맞았다. 다만 세 국면 사양도 구간별 자유 모형에 비해 기각되어(${comma(tR.stat, 1)}, 자유도 ${tR.df}), 같은 국면 안의 두 구간도 서로 같지 않다. Ⅳ장의 모의실험이 우려한 검정력의 부족은 실제 자료에서 문제가 되지 않았다. 실제 변화가 가정한 0.06보다 훨씬 컸기 때문이다.`));

  c.push(H2('6. 민감도 분석'));
  const srow = (s) => [s.spec, `${p1(s.top_share_2021)} → ${p1(s.top_share_2023)} → ${p1(s.top_share_2024)}`, ...IV.map((iv) => (s[`top_stay_${iv}`] === undefined || s[`top_stay_${iv}`] === null ? '–' : f2(s[`top_stay_${iv}`])))];
  c.push(...T('<표 30> 사양에 따른 앱 구매 상태의 비중과 유지확률', ['사양', '비중(%): 2021 → 2023 → 2024년', ...IV.map((iv) => `유지\n${iv}`)], rs.sensitivity.map(srow),
    [2700, 1870, 900, 900, 900, 900, 900], { align: ['left', 'center', 'center', 'center', 'center', 'center', 'center'], size: 16, notes: ['주: 앱 구매 상태는 앱 내 아이템 구입 확률이 가장 높은 상태이다. 네 상태 모형에서는 복합 구매 상태가 앱 구매 중심 상태와 영상·음악 다중 구독 상태로 나뉘며, 표의 값은 앞의 것이다.'] }));
  const sK4 = rs.sensitivity.find((s) => s.K === 4), sInv = rs.sensitivity.find((s) => s.spec === '완전 측정불변');
  c.push(P(`<표 30>은 여덟 가지 사양의 결과이다. 완전 측정불변, 비가중, 2021~2025년만 쓴 분석, 비대상을 결측으로 둔 분석, 영상을 지출과 무관한 가입 여부로 정의한 분석, 여섯 해에 모두 응답한 사람만 쓴 분석에서 앱 구매 상태의 유지확률은 모두 2021→2022년과 2022→2023년에 낮고 그 전후에 높았다. 네 상태 모형에서는 복합 구매 상태가 둘로 나뉘는데, 앱 구매 중심 상태의 유지확률은 2021→2022년 ${f2(sK4['top_stay_2021→2022'])}, 2022→2023년 ${f2(sK4['top_stay_2022→2023'])}로 같은 모양을 보인다. 결과의 방향은 사양에 좌우되지 않는다. 크기는 달라진다. 완전 측정불변 사양에서는 2023→2024년의 유지확률이 ${f2(sInv['top_stay_2023→2024'])}로 더 높게 나오는데, 2024년 영상 지표의 수준 변화를 상태 이동으로 읽기 때문이다.`));

  // 모형 적합 진단과 재검증(code/12_verify_real_results.py)
  const mf = csv('real_marginal_fit.csv');
  const vrText = fs.readFileSync(path.join(OUT, 'real_verification.csv'), 'utf8');   // 설명 칸에 쉼표가 있어 줄 단위로 센다
  const mfAbs = mf.map((r) => Math.abs(Number(r.diff_pp)));
  const mfMax = mf[mfAbs.indexOf(Math.max(...mfAbs))];
  const ITEM_KO = { paid_app: '유료 앱 구입', inapp_item: '앱 내 아이템 구입', paid_video: '영상 유료 이용', paid_music: '음악 유료 이용' };
  const nPass = (vrText.match(/,일치,/g) || []).length, nCheck = nPass + (vrText.match(/,불일치,/g) || []).length;
  c.push(P(`주 모형이 자료를 얼마나 잘 맞추는지도 점검하였다. 모형이 함의하는 연도별 지표 비율, 곧 상태 비중에 응답확률을 곱해 더한 값을 같은 가중치로 계산한 관측 비율과 견주면 평균 ${f1(mfAbs.reduce((a, b) => a + b, 0) / mfAbs.length)}%포인트, 최대 ${f1(Math.max(...mfAbs))}%포인트 어긋난다. 가장 큰 차이는 ${mfMax.wave}년의 ${ITEM_KO[mfMax.item]}으로, 모형은 ${f1(mfMax.implied_pct)}%, 관측값은 ${f1(mfMax.observed_pct)}%이다. 상태를 셋으로 제한하고 응답확률을 여러 해에 걸쳐 같게 묶은 데 따른 차이이며, BIC가 더 복잡한 모형을 선호한 것과 같은 사정이다. 따라서 <표 27>과 <표 28>의 추정값은 세 상태로 요약하였을 때의 근사로 읽어야 한다. 본 장의 핵심 결과가 이 근사에 의존하는 정도는 크지 않다. 2절의 관측 전이율은 모형 없이 계산한 것인데 같은 모양을 보이기 때문이다.`));
  c.push(P(`끝으로 결과의 계산을 분석 스크립트와 다른 경로로 다시 수행하여 대조하였다. 원자료에서 직접 계산한 가중 비율이 보고서의 공표값과 일치하는지, 분석용 자료의 지표가 원자료에서 다시 만든 지표와 같은지, 다른 난수에서 출발한 재추정이 같은 해에 도달하는지, 추정 엔진의 개인별 로그우도가 가능한 잠재경로 729개를 모두 열거하여 계산한 값과 같은지 등 ${nCheck}개 항목을 검사하였고 ${nPass}개가 일치하였다(outputs/real_verification.csv).`));

  // ── 7. 가격 인상 노출과 구매의 지속 ──
  c.push(H2('7. 가격 인상 노출과 구매의 지속'));
  const lg = csv('real_exposure_logit.csv');
  const lq = (outcome, kind, term, idx = '주 지수') => lg.find((r) => r.outcome === outcome && r.kind.startsWith(kind) && r.term === term && r.index === idx);
  const es = (r) => `${f3(r.estimate)} (${f3(r.se)})`;
  const cm = rs.covariate_model;
  const rates = cm && cm.rates ? cm.rates : { video: 13.92, music: 12.025, webtoon: 20.0 };
  const kI = lq('앱 내 아이템 구입', '지속', '노출 × 가격 인상기'), kM = lq('음악 유료 이용', '지속', '노출 × 가격 인상기'), kA = lq('유료 앱 구입', '지속', '노출 × 가격 인상기');
  const kInv = lq('앱 내 아이템 구입', '지속', '노출 × 가격 인상기', '영상 제외 지수');
  c.push(P(`연구 질문 3은 가격 인상에 더 많이 노출된 이용자가 가격 인상기에 구매를 더 많이 그만두었는가이다. 노출 지수는 Ⅲ장 9절의 정의를 따르되 기준 시점을 2020년 조사로 하였다. 2020년에는 영상의 지불 유형 문항이 없으므로 영상 항목은 동영상 서비스 이용 여부로 대신하였고, 영상을 뺀 지수(음악과 웹툰·전자책만)를 함께 썼다. 유형별 인상률은 영상 ${f1(rates.video)}%, 음원 ${f1(rates.music)}%, 웹툰·웹소설 ${f1(rates.webtoon)}%이다. 분석 대상은 2020년에 응답하고 스마트폰 제조사가 확인된 사람이다.`));
  c.push(P('먼저 지표 수준에서 보았다. 어느 해에 구입한 사람이 다음 해에도 구입하였는지를 종속변수로 하는 로지스틱 회귀이며, 설명변수는 구간 더미, 표준화한 노출 지수, 노출 지수와 국면(가격 인상기, 이후)의 상호작용, 안드로이드 여부, 표준화한 연령이다. 연령을 넣은 것은 젊은 층일수록 노출 지수가 높고 2021년의 일시적 상승도 컸을 수 있기 때문이다. 앞 해의 횡단 가중치를 쓰고 표준오차는 가구 군집에 강건하게 계산하였다. 관심 계수는 노출 지수와 가격 인상기의 상호작용이며, 음수이면 노출이 큰 사람이 가격 인상기에 구매를 덜 이어 갔다는 뜻이다.'));
  const lrow = (outcome, kind) => { const a = lq(outcome, kind, '노출(이전 국면)'), b = lq(outcome, kind, '노출 × 가격 인상기'), d = lq(outcome, kind, '노출 × 이후');
    return [outcome, kind === '지속' ? '지속(앞 해 구입자)' : '진입(앞 해 비구입자)', comma(a.n), es(a), es(b), pv(b.p), es(d)]; };
  c.push(...T('<표 31> 가격 인상 노출 지수와 구매의 지속·진입: 로지스틱 회귀', ['지표', '표본', '개인×구간 수', '노출(이전 국면)', '노출 × 가격 인상기', 'p', '노출 × 이후'],
    [lrow('앱 내 아이템 구입', '지속'), lrow('앱 내 아이템 구입', '진입'), lrow('유료 앱 구입', '지속'), lrow('유료 앱 구입', '진입'), lrow('음악 유료 이용', '지속'), lrow('음악 유료 이용', '진입')],
    [1700, 1700, 1100, 1300, 1400, 600, 1270], { align: ['left', 'left', 'center', 'center', 'center', 'center', 'center'], size: 16, notes: ['주: 로그 오즈에 대한 노출 지수 1 표준편차의 효과, 괄호 안은 가구 군집에 강건한 표준오차. 구간 더미, 안드로이드, 연령을 함께 통제. 이전 국면은 2020→2021년, 가격 인상기는 2021→2022년과 2022→2023년, 이후는 2023→2024년과 2024→2025년. 자료: outputs/real_exposure_logit.csv(code/09_exposure_persistence.py).'] }));
  c.push(P(`결과는 분명하다(<표 31>). 앱 내 아이템을 구입하던 사람의 지속에 대한 상호작용은 ${f3(kI.estimate)}(표준오차 ${f3(kI.se)}, __p__ = ${pv(kI.p)})로 0과 구별되지 않고, 영상을 뺀 지수로도 ${f3(kInv.estimate)}(__p__ = ${pv(kInv.p)})이다. 유료 앱 구입은 ${f3(kA.estimate)}(__p__ = ${pv(kA.p)}), 음악 유료 이용은 ${f3(kM.estimate)}(__p__ = ${pv(kM.p)})이다. 가격 인상에 더 많이 노출된 이용자가 가격 인상기에 구매를 더 많이 그만두었다는 증거는 없다. 앱 내 구매의 지속률은 가격 인상기에 모든 이용자에게서 비슷하게 낮아졌고, 이는 가격 인상보다 모두에게 공통된 요인을 가리킨다. 새로 구입하기 시작한 쪽에서는 노출이 큰 사람이 가격 인상기에 오히려 더 많이 진입하였다(유료 앱 구입 ${f3(lq('유료 앱 구입', '진입', '노출 × 가격 인상기').estimate)}, 음악 유료 이용 ${f3(lq('음악 유료 이용', '진입', '노출 × 가격 인상기').estimate)}).`));
  if (cm && !cm.error) {
    const cc = csv('real_cov_coefficients.csv');
    const k = cc.find((r) => r.index.startsWith('주 지수') && r.origin === SL[2] && r.dest === SL[1] && r.covariate.startsWith('가격 인상 노출') && r.quantity === '가격 인상기 − 이전');
    c.push(P(`Ⅳ장 10절의 잠재상태 공변량 모형도 같은 자료(${comma(cm.n)}명)에 적합하였다. 그러나 이 모형은 원자료에서 안정적으로 추정되지 않았다. 추정은 수렴하였으나 정보행렬이 양의 정부호가 아니었고, 연령의 일부 계수와 영상을 뺀 지수를 쓴 사양의 일부 계수가 발산하였다. 드문 전이에 공변량 계수를 셋씩 둔 데 따른 분리 문제로 보인다. 복합 구매에서 구독 중심으로의 전이에 대한 노출 지수의 상호작용은 ${f3(k.estimate)}(표준오차 ${f3(k.se)})로, 부호는 노출이 큰 사람이 더 많이 떠났다는 가설과 반대였으나, 표준오차를 신뢰할 수 없으므로 본 연구는 이 모형의 결과를 결론의 근거로 삼지 않는다. 계수는 코드집의 outputs/real_cov_coefficients.csv에 있다. 모의자료에서 잘 작동한 모형이 원자료에서는 그렇지 못하였다는 점은 그 자체로 기록해 둘 결과이다.`));
  }

  c.push(H2('8. 결과의 해석'));
  c.push(P('원자료의 결과를 가격 인상의 영향으로 읽을 수 있는가. 세 가지 사실이 서로 다른 방향을 가리킨다. 첫째, 앱 구매가 활발한 상태에서의 이탈은 인앱결제 의무화와 가격 인상이 걸친 두 구간에 집중되었고, 이는 모형 없이 계산한 관측 전이율에서도, 여덟 가지 사양에서도 같았다. 연구명제 2가 예상한 방향이다. 둘째, 그러나 2022년에 실제로 값이 오른 것은 영상과 음원, 웹툰 서비스였는데 이 서비스들의 유료 이용은 줄지 않았다. 줄어든 것은 게임 아이템과 이모티콘처럼 규제 이전부터 인앱결제 대상이던 앱 내 구매이고, 온라인 게임 이용률도 같은 시기에 함께 낮아졌다. 가격이 오른 곳에서 구매가 줄었다는 대응 관계는 보이지 않는다. 셋째, 2021년은 앱 내 구매와 게임 이용이 일시적으로 높았던 해이므로 2021→2022년의 이탈에는 그 반동이 들어 있다.'));
  c.push(P('이 셋을 종합하면, 2021~2023년에 앱 내 구매가 덜 이어지고 덜 시작된 것은 사실이지만 그 원인을 2022년의 인앱 가격 인상으로 돌릴 근거는 약하다. 코로나19 시기에 늘었던 앱 내 구매, 특히 게임 관련 구매가 줄어든 것이 더 간명한 설명이다. 다만 2023년의 수준이 2020년보다 낮고 2022→2023년의 지속률도 2020→2021년보다 낮다는 점은 단순한 원상 복귀만으로 설명되지 않는다. 이 부분이 인앱결제 의무화 이후 앱 안의 결제 환경이 달라진 것과 관련이 있는지, 예컨대 사업자들이 웹 결제로 이용자를 유도하면서 앱 내 구매로 응답되는 결제가 줄었는지는 이 자료로 가릴 수 없다. 조사가 결제 경로를 묻지 않기 때문이다.'));
  c.push(P('2024년의 회복도 같은 주의가 필요하다. 2023→2024년에 복합 구매 상태의 유지확률이 크게 오르고 구독 중심에서 복합 구매로의 이동이 늘었는데, 같은 해에 여러 문항에서 지출이 있다는 응답이 한꺼번에 늘었다. 주 모형은 영상 문항의 변화만 측정의 변화로 처리하였으므로, 앱 구매 문항에도 같은 종류의 변화가 있었다면 2024년의 회복은 과대 추정되었을 것이다. 따라서 가장 믿을 수 있는 비교는 측정이 안정된 2020~2023년 안에서의 비교, 곧 2020→2021년과 그 뒤 두 구간의 비교이며, 그 비교는 2021년이 예외적인 해였다는 점에서 자유롭지 않다.'));
  return c;
};
