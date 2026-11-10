# -*- coding: utf-8 -*-
"""
14_audit_paper_numbers.py — 논문에 실린 수치의 전수 점검

논문의 수치는 두 종류다. (가) 빌드할 때 outputs/ 의 결과 파일에서 읽어 넣는 값, (나) 원고에 글자로 직접 적은 값.
(가)는 결과 파일을 그 출처(원자료, 사업자 자료, 반복 실험 기록)에서 다시 계산해 대조하고,
(나)는 하나씩 자료 파일의 값과 대조한다. 끝으로 완성된 워드 파일의 본문에 핵심 수치가 실제로 들어 있는지 확인한다.

출력 outputs/paper_audit.csv   (분류, 항목, 논문의 값, 다시 계산한 값, 판정)
실행 python code/14_audit_paper_numbers.py
"""
import json
import os
import re
import sys
import zipfile

import numpy as np
import pandas as pd
from scipy.stats import binomtest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lta_engine as L        # noqa: E402
import study_design as D      # noqa: E402

# 자체 시험(16_audit_selftest.py)이 결과 파일의 사본을 일부러 망가뜨려 넣을 수 있도록 경로를 환경변수로 바꿀 수 있게 한다.
OUT, DATA = os.environ.get('AUDIT_OUT', os.path.join(ROOT, 'outputs')), os.path.join(ROOT, 'data')
RAW = os.path.join(DATA, 'private', 'raw_kisdi')
rows = []


def rec(group, item, paper, recomputed, ok, note=''):
    rows.append(dict(group=group, item=item, paper=str(paper), recomputed=str(recomputed), result='일치' if ok else '불일치', note=note))


def close(a, b, tol):
    return abs(float(a) - float(b)) <= tol


def raw(y):
    yy = str(y)[2:]
    src = pd.read_csv(os.path.join(RAW, f'p{yy}v32_KMP_csv.csv'), encoding='cp949', low_memory=False, na_values=[' ', ''])
    d = pd.DataFrame({'pid': src['pid'].astype(int), 'hid': src['hid'].astype(int)})
    for c in ('wt', 'age', 'gender', 'c06006', 'c06007', 'c06010', 'd26001', 'd26051', 'd26052', 'd26053', 'd26055', 'd26057',
              'c05050', 'c05051', 'c05052', 'c05001', 'c05007'):
        if f'p{yy}{c}' in src.columns:                   # 그해 조사에 없는 문항은 열을 만들지 않는다
            d[c] = pd.to_numeric(src[f'p{yy}{c}'], errors='coerce')
    return d


def wrate(x, w, mask=None):
    m = x.notna() if mask is None else (x.notna() & mask)
    return 100 * w[m & (x == 1)].sum() / w[m].sum()


def wmean(x, w):
    m = x.notna()
    return float((x[m] * w[m]).sum() / w[m].sum())


R = {y: raw(y) for y in range(2020, 2026)}
r25 = R[2025]
nums = json.load(open(os.path.join(OUT, 'paper_numbers.json'), encoding='utf-8'))
rs = json.load(open(os.path.join(OUT, 'real_summary.json'), encoding='utf-8'))
s1 = json.load(open(os.path.join(OUT, 'prop1_summary.json'), encoding='utf-8'))
rv = json.load(open(os.path.join(OUT, 'reval_summary.json'), encoding='utf-8'))
cv = json.load(open(os.path.join(OUT, 'cov_summary.json'), encoding='utf-8'))
ev_text = open(os.path.join(DATA, 'policy_goal_outcome_evidence.csv'), encoding='utf-8-sig').read()
ev = pd.read_csv(os.path.join(DATA, 'policy_goal_outcome_evidence.csv'))
events = pd.read_csv(os.path.join(DATA, 'policy_events.csv'))

# ═════════════ 1. Ⅳ장 1절: 공표 집계치(표 6, 표 7, 그림 2·3) — 원자료로 대조 ═════════════
agg = pd.read_csv(os.path.join(DATA, 'kisdi_public_aggregates.csv'))
AGE = {'만 10대 미만': 1, '만 10-19세': 2, '만 20-29세': 3, '만 30-39세': 4, '만 40-49세': 5, '만 50-59세': 6, '만 60-69세': 7, '만 70세 이상': 8}
VAR = dict(paid_app='c06006', inapp_item='c06007', ott_svod='d26053', ott_tvod='d26052', ott_avod='d26051', music_use='c05051', game_use='c05052',
           news_ebook_webtoon_use='c05050', ott_use='d26001')
worst, nchk, bad = 0.0, 0, []
for _, a in agg.iterrows():
    if a.indicator not in VAR or int(a.year) not in R:
        continue
    d = R[int(a.year)]
    if VAR[a.indicator] not in d.columns:
        continue
    m = pd.Series(True, index=d.index)
    if a.group_type == '연령':
        m = d['age'] == AGE[a.group]
    elif a.group_type == '성별':
        m = d['gender'] == (1 if a.group == '남성' else 2)
    got = wrate(d[VAR[a.indicator]], d['wt'], m)
    nchk += 1
    diff = abs(got - a.value_pct)
    worst = max(worst, diff)
    if diff > 0.06:
        bad.append(f'{a.indicator}/{a.group}/{int(a.year)}: 자료 {a.value_pct}, 원자료 {got:.2f}')
rec('Ⅳ.1 공표 집계치', f'kisdi_public_aggregates.csv의 경험률 {nchk}건(전체·연령·성별) = 원자료 가중 비율', f'{nchk}건', f'최대 차이 {worst:.3f}%p', not bad, '; '.join(bad[:4]))
rec('Ⅳ.1 공표 집계치', '앱 관련 구입 경험자의 연간 지출 평균(원)', '13,548', f"{1000 * wmean(r25['c06010'], r25['wt']):,.0f}", close(1000 * wmean(r25['c06010'], r25['wt']), 13548, 1))
rec('Ⅳ.1 공표 집계치', '월정액 동영상 서비스의 월평균 지출(원)', '11,225', f"{1000 * wmean(r25['d26057'], r25['wt']):,.0f}", close(1000 * wmean(r25['d26057'], r25['wt']), 11225, 1))
ret = pd.read_csv(os.path.join(DATA, 'kisdi_panel_retention.csv'))
okr, det = True, []
for y in range(2021, 2026):
    prev_ids, ids = set(R[y - 1]['pid']), set(R[y]['pid'])
    kept = len(prev_ids & ids)
    row = ret[ret.year == y].iloc[0]
    good = kept == int(row.retained_from_prev) and len(ids) == int(row.respondents) and close(100 * kept / len(prev_ids), row.retention_pct, 0.06)
    okr &= good
    det.append(f'{y}: {kept:,}명 {100 * kept / len(prev_ids):.1f}%')
rec('Ⅳ.1 공표 집계치', '표 7 유지 인원·유지율·응답자 수(2021~2025) = 원자료의 개인 번호 대조', '표 7', ', '.join(det), okr)
rec('Ⅲ.2 자료', '2025년 조사 가구 수와 개인 수', '3,956가구 8,411명', f"{r25['hid'].nunique():,}가구 {len(r25):,}명", r25['hid'].nunique() == 3956 and len(r25) == 8411)

# ═════════════ 2. Ⅳ장 9절: 2021~2025 공표 수치와 재검증 ═════════════
pub = pd.read_csv(os.path.join(DATA, 'kisdi_published_series_2021_2025.csv'))
V2 = dict(paid_app='c06006', inapp_item='c06007', ott_svod='d26053', music_use='c05051', game_use='c05052')
worst_p, worst_n = 0.0, 0.0
for _, a in pub.iterrows():
    d = R[int(a.year)]
    x = d[V2[a.indicator]]
    m = x.notna()
    worst_p = max(worst_p, abs(wrate(x, d['wt']) - a.published_pct))
    worst_n = max(worst_n, abs(d['wt'][m & (x == 1)].sum() - a.n_experienced), abs(d['wt'][m].sum() - a.base_n))
rec('Ⅳ.9 재검증', f'공표 경험률 {len(pub)}건 = 원자료 가중 비율', f'{len(pub)}건', f'최대 차이 {worst_p:.3f}%p', worst_p <= 0.06)
rec('Ⅳ.9 재검증', '공표 사례 수·분모 = 원자료 가중 합', f'{len(pub)}건', f'최대 차이 {worst_n:.2f}명', worst_n <= 0.6)
Nresp = {y: len(R[y]) for y in range(2021, 2026)}
V3 = dict(paid_app='c06006', inapp_item='c06007', paid_video='d26053', paid_music='c05051')
worst_s = max(abs(100 * R[y]['wt'][R[y][V3[it]] == 1].sum() / Nresp[y] - rv['real_series_pct'][it][i]) for it in V3 for i, y in enumerate(range(2021, 2026)))
rec('Ⅳ.9 재검증', '표 18 실제 수치(전체 응답자 대비 %) 20건 = 원자료', '표 18', f'최대 차이 {worst_s:.3f}%p', worst_s <= 0.06)
sv = [wrate(R[y]['d26053'], R[y]['wt']) for y in (2023, 2024)]
gm = [wrate(R[y]['c05052'], R[y]['wt']) for y in (2021, 2022)]
rec('Ⅳ.9 재검증', '본문: 월정액 가입률 30.3% → 54.3%(2023→2024)', '30.3 → 54.3', f'{sv[0]:.1f} → {sv[1]:.1f}', close(sv[0], 30.3, 0.06) and close(sv[1], 54.3, 0.06))
rec('Ⅳ.9 재검증', '본문: 온라인 게임 이용률 31.0% → 21.7%(2021→2022)', '31.0 → 21.7', f'{gm[0]:.1f} → {gm[1]:.1f}', close(gm[0], 31.0, 0.06) and close(gm[1], 21.7, 0.06))

# ═════════════ 3. Ⅳ장 8절: 연구명제(사업자 자료) — firm_strategy.csv 에서 다시 계산 ═════════════
st = pd.read_csv(os.path.join(OUT, 'prop1_service_types.csv'))
fs_ = pd.read_csv(os.path.join(DATA, 'firm_strategy.csv'))
svc = fs_[~fs_['sector'].astype(str).str.contains('앱마켓')] if fs_['sector'].astype(str).str.contains('앱마켓').any() else fs_.iloc[:len(st)]
coded = st[st.pre_type.notna() & st.post_type.notna()]
changed = int(coded.payment_changed.astype(str).str.lower().isin(['true', '1', '1.0']).sum()) if 'payment_changed' in coded else None
rec('Ⅳ.8 연구명제', '결제 방식을 전후 모두 코딩한 서비스 수', s1['n_coded_payment'], len(coded), len(coded) == s1['n_coded_payment'] == 19)
rec('Ⅳ.8 연구명제', '결제 방식이 달라진 서비스 수', f"{s1['payment_changed']['k']}/{s1['payment_changed']['n']}", f'{changed}/{len(coded)}', changed == s1['payment_changed']['k'] == 16)
T16 = [('앱 내 자체결제', '인앱결제 수용·가격 인상', 9), ('앱 내 자체결제', '인앱결제 수용·가격 변화 미확인', 3), ('앱 내 자체결제', '제3자 결제 도입', 1),
       ('구글 인앱결제', '인앱결제 수용', 2), ('구글 인앱결제', '인앱결제 유지·자체 채널 병행', 3), ('앱 내 결제 없음(웹 전용)', '앱 내 결제 제거(웹 전용)', 1)]
for pre, post, k in T16:
    got = int(((coded.pre_type == pre) & coded.post_type.astype(str).str.startswith(post)).sum())
    rec('Ⅳ.8 연구명제', f'표 16: {pre} → {post}', k, got, got == k)
price = fs_[fs_.android_price_change_date.astype(str).str.startswith('2022') & fs_.android_price_old_krw.notna() & fs_.android_price_new_krw.notna()]
pct = 100 * (price.android_price_new_krw / price.android_price_old_krw - 1)
pr = s1['price_change_pct_raised']
rec('Ⅳ.8 연구명제', '2022년 인앱 가격 변경 서비스 수와 인상 수', f"{s1['price_raised']['k']}/{s1['price_raised']['n']}", f'{int((pct > 0).sum())}/{len(pct)}', len(pct) == 10 and (pct > 0).all())
rec('Ⅳ.8 연구명제', '인상률 중위·최소·최대(%)', f"{pr['median']:.1f} / {pr['min']:.1f} / {pr['max']:.1f}", f'{pct.median():.1f} / {pct.min():.1f} / {pct.max():.1f}',
    close(pct.median(), pr['median'], 1e-6) and close(pct.min(), pr['min'], 1e-6) and close(pct.max(), pr['max'], 1e-6))
be = 100 * (1 - price.android_price_old_krw / price.android_price_new_krw)
rec('Ⅳ.8 연구명제', '손익분기 수수료율 중위(%)', f"{s1['breakeven_fee_pct_raised']['median']:.1f}", f'{be.median():.1f}', close(be.median(), s1['breakeven_fee_pct_raised']['median'], 1e-6))
rec('Ⅳ.8 연구명제', '완전 전가 인상률: 15% → , 30% → (%)', f"{s1['full_passthrough_rise_pct']['fee15']:.1f} / {s1['full_passthrough_rise_pct']['fee30']:.1f}", f'{100 * .15 / .85:.1f} / {100 * .3 / .7:.1f}',
    close(s1['full_passthrough_rise_pct']['fee15'], 100 * .15 / .85, 1e-9) and close(s1['full_passthrough_rise_pct']['fee30'], 100 * .3 / .7, 1e-9))
mc_ = s1['mcnemar']
p_mc = binomtest(mc_['iap_to_not'], mc_['not_to_iap'] + mc_['iap_to_not'], 0.5).pvalue
rec('Ⅳ.8 연구명제', '맥니마 정확검정 p', f"{mc_['p_exact']:.5f}", f'{p_mc:.5f}', close(p_mc, mc_['p_exact'], 1e-12))
rec('Ⅳ.8 연구명제', '부호검정 p(10개 모두 인상)', f"{s1['sign_test_p']:.5f}", f'{binomtest(10, 10, 0.5).pvalue:.5f}', close(binomtest(10, 10, 0.5).pvalue, s1['sign_test_p'], 1e-12))
for label, token in (('매출 비중 구글 67.5%', '67.5'), ('애플 28.2%', '28.2'), ('원스토어 2.9%', '2.9'), ('거래액 8조 1,952억 원', '81952'), ('과도한 수수료 70.4%', '70.4'),
                     ('소비자 추가 부담 2,300억 원', '2300'), ('과징금 구글 429억', '429'), ('애플 208.1억', '208.1'), ('합계 637.1억', '637.1'),
                     ('산출 과징금 구글 2,545.7억', '2545.7'), ('애플 2,256.1억', '2256.1'), ('Chang & Miller 표준오차 0.064', '0.064'), ('표준오차 0.079', '0.079'),
                     ('다운로드 0.002', '0.002'), ('매출 −0.093', '-0.093')):
    rec('서론·표 17 사실관계', f'{label} — 증거 자료(policy_goal_outcome_evidence.csv)에 수록', token, '있음' if token in ev_text else '없음', token in ev_text)
T1 = [('2020-09-28', '구글'), ('2021-09-14', '개정법'), ('2021-11-04', '구글'), ('2022-03-15', '시행령'), ('2022-06-01', '구글'), ('2022-06-30', '애플'),
      ('2022-08-16', '사실조사'), ('2023-10-06', '시정조치안'), ('2025-10-01', '방송미디어통신위원회'), ('2026-03-04', '구글'), ('2026-10-28', '과징금'),
      ('2024-03-07', 'DMA'), ('2025-04-23', '애플'), ('2025-11-13', '한미')]
for date, kw in T1:
    hit = events[(events.date == date) & events.label.str.contains(kw)]
    rec('서론·표 1 날짜', f'{date} {kw}', date, '정책 연표에 있음' if len(hit) else '없음', len(hit) == 1)

# ═════════════ 4. Ⅲ장: 모의패널 설계값(표 4) ═════════════
ok4 = (D.N_DESIGN == 10302 and np.allclose(D.RETENTION, [0.946, 0.945, 0.948, 0.848]) and np.allclose(D.PI0, [0.55, 0.33, 0.12])
       and np.allclose(D.THETA, [[0.005, 0.03, 0.30], [0.02, 0.10, 0.65], [0.10, 0.85, 0.90], [0.03, 0.38, 0.70]])
       and np.allclose(D.A_BASE, [[0.88, 0.10, 0.02], [0.06, 0.86, 0.08], [0.03, 0.12, 0.85]]) and D.DELTA_MAIN == 0.06 and D.REENTRY == 0.30 and D.ITEM_MISSING == 0.01)
rec('Ⅲ.4 설계값', '표 4의 표본 크기·유지율·상태 비중·응답확률·전이확률·변화 크기 = study_design.py', '표 4', '코드의 상수', ok4)
At = D.transition_matrices()
rec('Ⅲ.4 설계값', '표 4: S3에서(뒤 국면) 0.03 / 0.18 / 0.79', '0.03 / 0.18 / 0.79', ' / '.join(f'{v:.2f}' for v in At[3, 2]), np.allclose(At[3, 2], [0.03, 0.18, 0.79]))
rec('Ⅲ.4 설계값', '유지율(공표값 94.6, 94.5, 94.8, 84.8%) = 표 7', '94.6 94.5 94.8 84.8', ' '.join(str(ret[ret.year == y].retention_pct.iloc[0]) for y in range(2021, 2025)),
    all(close(ret[ret.year == y].retention_pct.iloc[0], v, 1e-9) for y, v in zip(range(2021, 2025), [94.6, 94.5, 94.8, 84.8])))

# ═════════════ 5. Ⅳ장 2~7절: 모의자료 결과 — 모의패널에서 다시 추정, 반복 기록에서 다시 집계 ═════════════
syn = pd.read_csv(os.path.join(DATA, 'synthetic_panel_long.csv'))
Ys, _ = L.panel_to_array(syn, 'id', 'wave', D.ITEMS, D.WAVES)
f3s = L.fit(Ys, 3, n_starts=10, n_jobs=-2)
rec('Ⅳ.2~6 모의패널', '모의패널 개인 수와 개인×시점 관측 수', f"{nums['run']['n_persons']:,} / {nums['run']['person_waves']:,}", f'{Ys.shape[0]:,} / {int((~np.isnan(Ys).all(2)).sum()):,}',
    Ys.shape[0] == nums['run']['n_persons'] and int((~np.isnan(Ys).all(2)).sum()) == nums['run']['person_waves'])
rec('Ⅳ.2~6 모의패널', '세 상태 모형의 로그우도(다시 적합)', f"{nums['py']['loglik_het']:.3f}", f"{f3s['loglik']:.3f}", close(f3s['loglik'], nums['py']['loglik_het'], 5e-3))
rcross = [c for c in nums['cross'] if c['quantity'] == 'loglik_het']
rec('Ⅳ.6 교차검증', '파이썬·R·LMest 로그우도의 일치(소수 셋째 자리)', ', '.join(f"{c['source']} {c['value']:.3f}" for c in rcross), f"{f3s['loglik']:.3f}",
    all(close(c['value'], f3s['loglik'], 5e-3) for c in rcross))
truth_err = float(np.abs(f3s['theta'][0] - D.THETA).max())
rec('Ⅳ.4 모의패널', '응답확률 최대 오차', f"{nums['run']['max_abs_err']['theta']:.3f}", f'{truth_err:.3f}', close(truth_err, nums['run']['max_abs_err']['theta'], 1e-3))
diag = np.array([f3s['A'][t, k, k] for t in range(4) for k in range(3)])
rec('Ⅳ.5 모의패널', '본문: 대각선 유지확률 0.78~0.90', '0.78 ~ 0.90', f'{diag.min():.2f} ~ {diag.max():.2f}', f'{diag.min():.2f}' == '0.78' and f'{diag.max():.2f}' == '0.90')
mcr = pd.read_csv(os.path.join(OUT, 'mc_replicates.csv'))
worst_mc = 0.0
for m in nums['mc']:
    q = mcr[(mcr.N == m['N']) & (np.abs(mcr.delta - m['delta']) < 1e-9)]
    worst_mc = max(worst_mc, abs((q.lr_p < 0.05).mean() - m['reject_rate']), abs((q.lr2_p < 0.05).mean() - m['reject_rate_regime']), abs(len(q) - m['reps']) / 1000)
rec('Ⅳ.7 몬테카를로', '표 15 기각률 24개(총괄·초점 × 12조건) = 반복 기록에서 다시 집계', '표 15', f'최대 차이 {worst_mc:.1e}', worst_mc < 1e-9)
mck = pd.read_csv(os.path.join(OUT, 'mc_kselect_replicates.csv'))
s3occ = [o['estimate'] for o in nums['occ'] if o['state'].startswith('S3')]
rec('Ⅳ.7 본문', '모의패널에서 복합 구매 상태의 비중 11~17%', '11 ~ 17', f'{100 * min(s3occ):.0f} ~ {100 * max(s3occ):.0f}', f'{100 * min(s3occ):.0f}' == '11' and f'{100 * max(s3occ):.0f}' == '17')
m500 = sorted([m for m in nums['mc'] if m['N'] == 500], key=lambda m: m['delta'])
rec('Ⅳ.7 본문', '500명 조건에서는 변화가 커져도 기각률이 높아지지 않음', '높아지지 않음', f"초점 검정 {m500[0]['reject_rate_regime']:.3f} → {m500[-1]['reject_rate_regime']:.3f}, 총괄 {m500[0]['reject_rate']:.3f} → {m500[-1]['reject_rate']:.3f}",
    m500[-1]['reject_rate_regime'] <= m500[0]['reject_rate_regime'] + 2 * m500[0]['reject_mcse_regime'] and m500[-1]['reject_rate'] <= m500[0]['reject_rate'] + 2 * m500[0]['reject_mcse'])
d8 = max(abs(m['shift_mean'] - m['delta']) for m in nums['mc'] if m['N'] == 8000)
rec('Ⅳ.7 본문', '8,000명 조건에서 변화 추정값의 평균이 심어 둔 값과 0.002 이내', '< 0.002', f'{d8:.4f}', d8 < 0.002)
rec('Ⅳ.7 본문', 'BIC가 세 표본 크기 모두에서 참값(세 상태)을 고른 비율이 같음', f"{nums['mck'][0]['pct_bic_k3']:.1f}%", ', '.join(f"{m['pct_bic_k3']:.1f}" for m in nums['mck']), len({m['pct_bic_k3'] for m in nums['mck']}) == 1)
bics = {s_['K']: s_['BIC'] for s_ in nums['sel']}
rec('Ⅳ.3 모의패널', 'BIC가 가장 낮은 상태 수(모의패널)', nums['run']['K_selected'], min(bics, key=bics.get), min(bics, key=bics.get) == nums['run']['K_selected'] == 3)
rec('Ⅲ.6 방법', '무작위 초기값 10개, 부트스트랩 500회', '10 / 500', f"{nums['run']['n_starts']} / {nums['run']['n_boot']}", nums['run']['n_starts'] == 10 and nums['run']['n_boot'] == 500)
rec('서론·표 1 사실관계', '2023년 시정조치안: 구글 475억 + 애플 205억 = 최대 680억 원', '680', 475 + 205, 475 + 205 == 680 and '680' in ev_text, '475억·205억의 내역은 증거 자료에 없고 합계 680억만 수록. 본문은 당시 보도에 근거')
rec('Ⅲ.7 몬테카를로', '본문: 반복 모의자료 2,700개(실험 A 12조건 × 200 + 실험 B 3조건 × 100)', '2,700', f'{len(mcr) + len(mck):,}', len(mcr) + len(mck) == 2700)

# ═════════════ 6. Ⅳ장 10절: 공변량 모형(모의) ═════════════
mm = {m['model'].split(' ')[0]: m for m in cv['models']}          # 'M2'와 민감도 사양 'M2s'를 구분
rec('Ⅳ.10 공변량(모의)', '우도비: 공변량 전체(M0 대 M1)', f"{cv['lr_covariates']['stat']:.1f}", f"{2 * (mm['M1']['loglik'] - mm['M0']['loglik']):.1f}", close(2 * (mm['M1']['loglik'] - mm['M0']['loglik']), cv['lr_covariates']['stat'], 1e-6))
rec('Ⅳ.10 공변량(모의)', '우도비: 상호작용(M1 대 M2)', f"{cv['lr_interaction']['stat']:.1f}", f"{2 * (mm['M2']['loglik'] - mm['M1']['loglik']):.1f}", close(2 * (mm['M2']['loglik'] - mm['M1']['loglik']), cv['lr_interaction']['stat'], 1e-6))
cmc = pd.read_csv(os.path.join(OUT, 'cov_mc_replicates.csv'))
worst_c = max(max(abs((cmc[(cmc.N == m['N']) & (cmc.alt == m['alt'])].lr_p < 0.05).mean() - m['lr_reject']), abs((cmc[(cmc.N == m['N']) & (cmc.alt == m['alt'])].wald_p < 0.05).mean() - m['wald_reject'])) for m in cv['monte_carlo'])
rec('Ⅳ.10 공변량(모의)', '표 23 기각률 8개 = 반복 기록에서 다시 집계', '표 23', f'최대 차이 {worst_c:.1e}', worst_c < 1e-9)
src6 = open(os.path.join(HERE, '06_covariate_lta.py'), encoding='utf-8').read()
design_ok = all(s in src6 for s in ['video=0.45', 'music=0.25', 'webtoon=0.25', 'game=0.20', 'P_ANDROID = 0.72', '(2, 1, 0): 0.50', '(2, 0, 0): 0.30', '(1, 0, 0): 0.25', '(2, 1, 1): 0.30'])
rec('Ⅳ.10 공변량(모의)', '본문의 가정값(이용률 45·25·25·20%, 안드로이드 72%, 효과 0.50·0.30·0.25·0.30) = 스크립트의 상수', '본문', '06_covariate_lta.py', design_ok)
rates = cv['sector_price_increase_pct']
sec = price.groupby('sector').apply(lambda g: (100 * (g.android_price_new_krw / g.android_price_old_krw - 1)).median())
rec('Ⅳ.10·Ⅴ.7 인상률', '유형별 인상률 중위: 영상 / 음원 / 웹툰(%)', f"{rates['video']:.1f} / {rates['music']:.1f} / {rates['webtoon']:.1f}", f"{sec['영상']:.1f} / {sec['음원']:.1f} / {sec['웹툰·웹소설']:.1f}",
    close(sec['영상'], rates['video'], 0.01) and close(sec['음원'], rates['music'], 0.01) and close(sec['웹툰·웹소설'], rates['webtoon'], 0.01),
    '중간 파일(prop1_service_types.csv)이 인상률을 소수 둘째 자리로 저장하므로 0.01 이내를 일치로 본다')

# ═════════════ 7. Ⅴ장: 원자료 분석 — 별도 검증(12 스크립트) 결과와 본문에 직접 적은 값 ═════════════
ver = pd.read_csv(os.path.join(OUT, 'real_verification.csv'))
rec('Ⅴ 원자료', '12_verify_real_results.py의 검사(공표값 대조, 지표 재구성, 재추정, 우도 전수 열거 등)', f"{(ver.result == '일치').sum()}개 일치", f"불일치 {(ver.result == '불일치').sum()}개", (ver.result != '불일치').all())
panel = pd.read_csv(os.path.join(DATA, 'private', 'consumer_panel.csv'))
rec('Ⅴ 원자료', '개인 수 / 가구 수 / 개인×연도 관측 / 여섯 해 모두 응답', f"{rs['n_persons']:,} / {rs['n_households']:,} / {rs['n_person_waves']:,} / {rs['n_all_waves']:,}",
    f"{panel.id.nunique():,} / {panel.sort_values('wave').groupby('id').hid.first().nunique():,} / {len(panel):,} / {int((panel.groupby('id').wave.nunique() == 6).sum()):,}",
    panel.id.nunique() == rs['n_persons'] and len(panel) == rs['n_person_waves'] and int((panel.groupby('id').wave.nunique() == 6).sum()) == rs['n_all_waves']
    and panel.sort_values('wave').groupby('id').hid.first().nunique() == rs['n_households'])
rec('Ⅲ.1 표 2', '표 2에 직접 적은 11,362명, 4,472가구', '11,362 / 4,472', f"{rs['n_persons']:,} / {rs['n_households']:,}", rs['n_persons'] == 11362 and rs['n_households'] == 4472)
prev = {int(p['wave']): p for p in rs['prevalence']}
worst_v = 0.0
for y in range(2020, 2026):
    d = R[y]
    w = d['wt']
    mine = dict(paid_app=100 * w[d['c06006'] == 1].sum() / w.sum(), inapp_item=100 * w[d['c06007'] == 1].sum() / w.sum(),
                paid_music=100 * w[(d['c05051'] == 1) & (d['c05007'].fillna(0) > 0)].sum() / w.sum(), use_game=100 * w[d['c05052'] == 1].sum() / w.sum(),
                paid_webtoon=100 * w[(d['c05050'] == 1) & (d['c05001'].fillna(0) > 0)].sum() / w.sum())
    if y > 2020:
        mine['paid_video'] = 100 * w[((d['d26053'] == 1) & (d['d26057'].fillna(0) > 0)) | ((d['d26052'] == 1) & (d['d26055'].fillna(0) > 0))].sum() / w.sum()
    worst_v = max(worst_v, max(abs(v - prev[y][k]) for k, v in mine.items()))
rec('Ⅴ.1 표 24', '연도별 가중 비율 35건(지표 4개와 참고 2개 × 6개 연도) = 원자료에서 다시 계산', '표 24', f'최대 차이 {worst_v:.3f}%p', worst_v <= 0.006)
th0 = np.array(rs['main']['theta_2020_2023'])
A = np.array(rs['main']['A'])
rec('Ⅴ.4 본문', '저소비 상태의 네 지표 확률이 모두 0.03 아래(2023년까지)', '< 0.03', f'최대 {th0[:, 0].max():.3f}', th0[:, 0].max() < 0.03)
rec('Ⅴ.5 본문', '복합 구매 → 저소비가 어느 구간에서나 0.1 미만', '< 0.1', f'최대 {A[:, 2, 0].max():.3f}', A[:, 2, 0].max() < 0.1)
rec('Ⅴ.6 본문', '민감도 사양의 수', '여덟 가지', len(rs['sensitivity']), len(rs['sensitivity']) == 8)
sens = rs['sensitivity']
dirs = all((s.get('top_stay_2021→2022') is not None and s['top_stay_2021→2022'] < s['top_stay_2023→2024'] and s['top_stay_2022→2023'] < s['top_stay_2023→2024']
            and (s.get('top_stay_2020→2021') is None or (s['top_stay_2021→2022'] < s['top_stay_2020→2021'] and s['top_stay_2022→2023'] < s['top_stay_2020→2021']))) for s in sens)
rec('Ⅴ.6 본문', '모든 사양에서 가격 인상기의 유지확률이 그 전후보다 낮음', '여덟 사양 모두', '성립' if dirs else '성립하지 않는 사양 있음', dirs)
rec('Ⅴ.4 표 27', '부트스트랩 유효 횟수', '300', rs['bootstrap']['n_valid'], rs['bootstrap']['n_valid'] == 300)
con = {(c['transition'], c['contrast']): c for c in rs['contrasts']}
c1 = con[('복합 구매 → 구독 중심', '가격 인상기 − 이전')]
rec('Ⅴ.5 표 29', '복합 구매 → 구독 중심, 가격 인상기 − 이전 = 전이확률에서 다시 계산', f"{c1['estimate']:.3f}", f'{A[[1, 2], 2, 1].mean() - A[0, 2, 1]:.3f}', close(A[[1, 2], 2, 1].mean() - A[0, 2, 1], c1['estimate'], 2e-4))
tests = {t['test']: t for t in rs['tests']}
rec('Ⅴ.5 본문', '경계를 앞당긴 사양의 우도비가 사전 지정 사양보다 큼', '경계를 앞당긴 쪽이 더 잘 맞음',
    f"{[t['stat'] for k, t in tests.items() if '[0,1,1,1,1]' in k and k.startswith('초점')][0]:.1f} > {[t['stat'] for k, t in tests.items() if '[0,0,1,1,1]' in k and k.startswith('초점')][0]:.1f}",
    [t['stat'] for k, t in tests.items() if '[0,1,1,1,1]' in k and k.startswith('초점')][0] > [t['stat'] for k, t in tests.items() if '[0,0,1,1,1]' in k and k.startswith('초점')][0])
lg = pd.read_csv(os.path.join(OUT, 'real_exposure_logit.csv'))
kI = lg[(lg.outcome == '앱 내 아이템 구입') & lg.kind.str.startswith('지속') & (lg['index'] == '주 지수') & (lg.term == '노출 × 가격 인상기')].iloc[0]
rec('Ⅴ.7 본문', '노출 × 가격 인상기(앱 내 아이템 구입의 지속)가 0과 구별되지 않음', 'p > 0.05', f'{kI.estimate:.3f} (p = {kI.p:.3f})', kI.p > 0.05)

# ═════════════ 8. 초록·각주에 직접 적은 값 ═════════════
rec('초록·각주', '국문·영문 초록: 19개 중 16개, 10개 모두 인상, 중위 15.4%, 제3자 결제 1개', '16/19, 10/10, 15.4, 1',
    f"{s1['payment_changed']['k']}/{s1['payment_changed']['n']}, {s1['price_raised']['k']}/{s1['price_raised']['n']}, {pr['median']:.1f}, {s1['third_party_adopted']['k']}",
    s1['payment_changed']['k'] == 16 and s1['payment_changed']['n'] == 19 and s1['price_raised']['k'] == 10 and f"{pr['median']:.1f}" == '15.4' and s1['third_party_adopted']['k'] == 1)
rec('초록·각주', '각주: 인상률 10.1~20.0%(중위 15.4%)', '10.1 ~ 20.0', f"{pr['min']:.1f} ~ {pr['max']:.1f}", f"{pr['min']:.1f}" == '10.1' and f"{pr['max']:.1f}" == '20.0')
rec('초록·각주', '각주: exp(0.5) ≈ 1.65', '1.65', f'{np.exp(0.5):.2f}', f'{np.exp(0.5):.2f}' == '1.65')
rec('초록·각주', '각주: 잠재경로 729개(3의 6제곱)', '729', 3 ** 6, 3 ** 6 == 729)

# ═════════════ 9. 완성된 워드 파일에 핵심 수치가 들어 있는가 ═════════════
docx = os.environ.get('AUDIT_DOCX', os.path.join(ROOT, 'paper', '한국_인앱결제_LTA_논문_20261111.docx'))
xml = zipfile.ZipFile(docx).read('word/document.xml').decode('utf-8')
text = re.sub(r'<[^>]+>', '', xml.replace('</w:p>', '\n'))
man = {(m['item'], m['interval']): m for m in rs['manifest']}
occ = np.array(rs['main']['occupancy'])
keys = {
    '개인 수 11,362': f"{rs['n_persons']:,}", '가구 수 4,472': f"{rs['n_households']:,}",
    '복합 구매 유지확률 2020→21': f'{A[0, 2, 2]:.2f}', '유지확률 2021→22': f'{A[1, 2, 2]:.2f}', '유지확률 2023→24': f'{A[3, 2, 2]:.2f}',
    '가격 인상기 − 이전(S3→S2)': f"{c1['estimate']:.3f}", '그 구간 하한': f"{c1['lo']:.3f}", '그 구간 상한': f"{c1['hi']:.3f}",
    '앱 내 아이템 지속률 2020→21': f"{100 * man[('inapp_item', '2020→2021')]['persist']:.1f}%", '지속률 2021→22': f"{100 * man[('inapp_item', '2021→2022')]['persist']:.1f}%",
    '저소비 2020년 비중': f'{100 * occ[0, 0]:.1f}%', '복합 구매 2023년 비중': f'{100 * occ[3, 2]:.1f}%',
    '노출 × 가격 인상기': f'{kI.estimate:.3f}', '모의패널 로그우도': f"{abs(nums['py']['loglik_het']):,.3f}"[:10],
    '인상률 중위 15.4%': '15.4%', '검정력 0.330': f"{[m for m in nums['mc'] if m['N'] == 8000 and abs(m['delta'] - 0.06) < 1e-9][0]['reject_rate_regime']:.3f}",
    '재검증 최대 차이 31.1': f"{rv['design_vs_real_max_abs_diff_pp']:.1f}%포인트", '공변량 모의 추정 0.445': f"{cv['focus_interaction']['estimate']:.3f}",
}
missing = [k for k, v in keys.items() if v not in text]
rec('완성 파일', f'워드 파일 본문에 핵심 수치 {len(keys)}개가 결과 파일의 값 그대로 들어 있음', f'{len(keys)}개', f'빠진 것 {len(missing)}개', not missing, ', '.join(missing))
stale = [s for s in ['원자료는 확보되지 않았', '개인 원자료가 없으므로', '수렴하지 않아 결과를 제시하지', 'undefined', 'NaN', '[object'] if s in text]
rec('완성 파일', '낡은 문구나 깨진 값(원자료 미확보, undefined, NaN 등)이 본문에 없음', '없음', ', '.join(stale) if stale else '없음', not stale)

# ═════════════ 10. 출처 재확인(outputs/fact_check.csv)의 결과가 자료와 본문에 반영되었는가 ═════════════
fc_path = os.path.join(OUT, 'fact_check.csv')
if os.path.exists(fc_path):
    fc = pd.read_csv(fc_path)
    cnt = fc.status.value_counts().to_dict()
    rec('출처 재확인', '출처 페이지에서 다시 대조한 사실 수(확인/불일치/확인 불가)', '41건', f"확인 {cnt.get('확인', 0)}, 불일치 {cnt.get('불일치', 0)}, 확인 불가 {cnt.get('확인 불가', 0)}",
        len(fc) == 41 and fc.source_url.notna().all(), '불일치·확인 불가 항목: ' + ', '.join(fc[fc.status != '확인'].id))
    wv = fs_[fs_.service == '웨이브'].android_price_change_date.iloc[0]
    rec('출처 재확인', '불일치 항목(웨이브 시행일)이 자료에서 고쳐짐', '2022-04-01', wv, wv == '2022-04-01')
    gone = [s for s in ['시정명령 8개 항목', '법정 상한(매출액 2%)', '매출액의 2%라는 법정 상한', '업계 추산'] if s in text]
    rec('출처 재확인', '확인되지 않은 서술(시정명령 항목 수, 2% 상한에 따른 감액, 업계 추산)이 본문에 남아 있지 않음', '없음', ', '.join(gone) if gone else '없음', not gone)
    need = [s for s in ['4월 1일 9,000원', 'outputs/fact_check.csv', '2026년 3월 4일'] if s not in text]
    rec('출처 재확인', '엇갈린 보도(웨이브, FLO)와 영문 원문 게시일이 본문에 적혀 있음', '있음', '빠진 것: ' + ', '.join(need) if need else '있음', not need)
    flo = price.copy()
    flo.loc[flo.service == 'FLO', 'android_price_new_krw'] = 9900
    pf = 100 * (flo.android_price_new_krw / flo.android_price_old_krw - 1)
    rec('출처 재확인', 'FLO를 9,900원으로 둘 때의 인상률 중위·최대(본문 18.2%, 25.3%)', '18.2 / 25.3', f'{pf.median():.1f} / {pf.max():.1f}',
        f'{pf.median():.1f}' == '18.2' and f'{pf.max():.1f}' == '25.3' and '18.2%' in text and '25.3%' in text)

out = pd.DataFrame(rows)
out.to_csv(os.path.join(OUT, 'paper_audit.csv'), index=False, encoding='utf-8-sig')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 260); pd.set_option('display.max_colwidth', 70); pd.set_option('display.max_rows', 200)
print(out.drop(columns=['note']).to_string())
print(out.groupby(['group', 'result']).size().to_string())
print('불일치:', int((out.result == '불일치').sum()), '/', len(out))
bad_rows = out[out.result == '불일치']
if len(bad_rows):
    print(bad_rows.to_string())
