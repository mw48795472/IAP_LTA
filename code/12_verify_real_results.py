# -*- coding: utf-8 -*-
"""
12_verify_real_results.py — 원자료 분석 결과의 재검증

분석 스크립트(07, 08, 11)와 다른 경로로 다시 계산해 맞는지 본다.
  1. 원자료 → 공표값: 연도별 원자료 파일에서 직접 계산한 가중 비율이 보고서의 공표 경험률과 같은가
  2. 원자료 → 분석용 패널: consumer_panel.csv 의 지표가 원자료에서 다시 만든 값과 같은가
  3. 표 → 출처: real_parameter_table.csv 와 PPTX 표의 숫자가 real_summary.json 에서 다시 계산한 값과 같은가
  4. 확률의 정합성: 전이확률 행의 합 = 1, 상태 비중의 합 = 1, 다음 해 비중 = 올해 비중 × 전이행렬
  5. 재추정: 주 모형을 처음부터 다시 적합했을 때 저장된 추정값이 재현되는가
  6. 우도: 엔진이 계산한 개인별 로그우도가 모든 잠재경로를 열거해 계산한 값과 같은가(무작위 300명)
  7. 적합: 모형이 함의하는 연도별 지표 비율이 관측 비율과 가까운가
  8. 관측 전이율: 앱 내 아이템 구입의 지속률을 다른 방식으로 계산해도 같은가

출력 outputs/real_verification.csv
"""
import itertools
import json
import os
import re
import sys
import zipfile

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lta_engine as L  # noqa: E402

OUT = os.path.join(ROOT, 'outputs')
RAW = os.path.join(ROOT, 'data', 'private', 'raw_kisdi')
WAVES = [2020, 2021, 2022, 2023, 2024, 2025]
ITEMS = ['paid_app', 'inapp_item', 'paid_video', 'paid_music']
res = []


def check(group, name, ok, detail):
    res.append(dict(group=group, check=name, result='일치' if ok else '불일치', detail=detail))


# ── 1, 2. 원자료에서 직접 ────────────────────────────────────────────────
PUB = {  # 보고서 공표 경험률(%): 유료 앱, 앱 내 아이템(스마트 기기 이용자), 월정액 가입(OTT 이용자), 음악 이용(전체)
    2021: (7.3, 14.1, 20.7, 38.8), 2022: (4.2, 8.2, 26.9, 36.4), 2023: (4.0, 5.8, 30.3, 32.9),
    2024: (6.5, 14.2, 54.3, 30.3), 2025: (5.4, 15.4, 59.7, 28.0)}
PUB_N = {2020: 10302, 2021: 10154, 2022: 9941, 2023: 9757, 2024: 8693, 2025: 8411}
panel = pd.read_csv(os.path.join(ROOT, 'data', 'private', 'consumer_panel.csv'))
worst_pub, worst_panel, n_ok = 0.0, 0.0, True
for y in WAVES:
    yy = str(y)[2:]
    d = pd.read_csv(os.path.join(RAW, f'p{yy}v32_KMP_csv.csv'), encoding='cp949', low_memory=False, na_values=[' ', ''])
    w = pd.to_numeric(d[f'p{yy}wt'], errors='coerce')
    n_ok &= len(d) == PUB_N[y] and d['pid'].is_unique
    num = lambda c: pd.to_numeric(d[f'p{yy}{c}'], errors='coerce') if f'p{yy}{c}' in d.columns else pd.Series(np.nan, index=d.index)   # noqa: E731

    def rate(x):                                   # 응답한 사람 가운데 1의 가중 비율
        m = x.notna()
        return 100 * w[m & (x == 1)].sum() / w[m].sum()
    app, inapp, svod, music = num('c06006'), num('c06007'), num('d26053'), num('c05051')
    if y in PUB:
        got = (rate(app), rate(inapp), rate(svod), rate(music))
        worst_pub = max(worst_pub, max(abs(g - p) for g, p in zip(got, PUB[y])))
    # 분석용 지표를 원자료에서 다시 만든다
    spend = lambda c: num(c).fillna(0) > 0     # noqa: E731
    mine = pd.DataFrame({'id': d['pid'].astype(int),
                         'paid_app': (app == 1).astype(float), 'inapp_item': (inapp == 1).astype(float),
                         'paid_video': (((svod == 1) & spend('d26057')) | ((num('d26052') == 1) & spend('d26055'))).astype(float) if y > 2020 else np.nan,
                         'paid_music': ((music == 1) & spend('c05007')).astype(float)}).set_index('id')
    theirs = panel[panel.wave == y].set_index('id')[ITEMS].loc[mine.index]
    diff = (mine[ITEMS] - theirs).abs()
    same_na = (mine[ITEMS].isna() == theirs.isna()).all().all()
    worst_panel = max(worst_panel, float(np.nanmax(diff.to_numpy())) if diff.notna().any().any() else 0.0)
    n_ok &= bool(same_na)
check('원자료', '연도별 응답자 수와 개인 번호의 유일성(6개 연도)', n_ok, ', '.join(f'{y}: {PUB_N[y]:,}' for y in WAVES))
check('원자료', '원자료의 가중 비율 = 보고서 공표 경험률(5개 연도 × 4개 지표)', worst_pub <= 0.05, f'최대 차이 {worst_pub:.3f}%포인트')
check('원자료', '분석용 패널의 지표 = 원자료에서 다시 만든 지표(57,258건 × 4)', worst_panel == 0, f'다른 값 {int(worst_panel)}건')

# ── 3. 표와 출처 ─────────────────────────────────────────────────────────
rs = json.load(open(os.path.join(OUT, 'real_summary.json'), encoding='utf-8'))
m = rs['main']
A, occ = np.array(m['A']), np.array(m['occupancy'])
th0, th1 = np.array(m['theta_2020_2023']), np.array(m['theta_2024_2025'])
expect = [occ[0], th0[0], th0[1], th0[2], th1[2], th0[3]]
for a in range(3):
    for idx in ([0], [1, 2], [3, 4]):
        expect.append(A[idx, a, :].mean(0))
expect = np.array(expect)
tab = pd.read_csv(os.path.join(OUT, 'real_parameter_table.csv'))
tv = tab[['S1 저소비', 'S2 구독 중심', 'S3 복합 구매']].to_numpy()
check('표', '표 CSV 45개 값 = 요약 결과에서 다시 계산한 값', np.abs(tv - expect).max() < 1e-9, f'최대 차이 {np.abs(tv - expect).max():.1e}')
px = os.path.join(ROOT, 'paper', '실자료_추정값_표.pptx')
if os.path.exists(px):
    xml = zipfile.ZipFile(px).read('ppt/slides/slide1.xml').decode('utf-8')
    nums = np.array([float(x) for x in re.findall(r'<a:t>(\d\.\d{3})</a:t>', xml)])
    ok = len(nums) == 45 and np.abs(nums - np.round(expect, 3).ravel()).max() < 1e-9
    check('표', 'PPTX 표의 숫자 45개 = 같은 값(소수 셋째 자리)', ok, f'읽은 숫자 {len(nums)}개')

# ── 4. 확률의 정합성 ─────────────────────────────────────────────────────
check('정합성', '전이확률 각 행의 합 = 1(5개 구간 × 3개 상태)', np.abs(A.sum(2) - 1).max() < 2e-4, f'최대 편차 {np.abs(A.sum(2) - 1).max():.1e}')
check('정합성', '표의 국면 평균 전이확률 각 행의 합 = 1', np.abs(tv[6:].sum(1) - 1).max() < 2e-4, f'최대 편차 {np.abs(tv[6:].sum(1) - 1).max():.1e}')
check('정합성', '연도별 상태 비중의 합 = 1', np.abs(occ.sum(1) - 1).max() < 2e-4, f'최대 편차 {np.abs(occ.sum(1) - 1).max():.1e}')
step = max(np.abs(occ[t] @ A[t] - occ[t + 1]).max() for t in range(5))
check('정합성', '다음 해 상태 비중 = 올해 비중 × 전이행렬', step < 5e-4, f'최대 차이 {step:.1e}(저장 값의 반올림 범위)')

# ── 5. 재추정 ────────────────────────────────────────────────────────────
Y, ids = L.panel_to_array(panel, 'id', 'wave', ITEMS, WAVES)
first = panel.sort_values('wave').groupby('id').first().loc[ids]
W = (first['wt'] / first['wt'].mean()).to_numpy()
TG = np.zeros((6, 4), int)
TG[4:, 2] = 1
fit = L.fit(Y, 3, n_starts=12, w=W, invariant=False, t_groups=TG, n_jobs=-2, maxit=2500, tol=1e-8, seed=777)     # 분석 때와 다른 난수
d_ll = abs(fit['loglik'] - m['loglik'])
d_par = max(np.abs(fit['A'] - A).max(), np.abs(fit['theta'][0] - th0).max(), np.abs(fit['theta'][-1] - th1).max(),
            np.abs(L.state_occupancy(fit['pi'], fit['A']) - occ).max())
check('재추정', '다른 난수로 다시 적합한 로그우도 = 저장된 값', d_ll < 1e-2, f"다시 적합 {fit['loglik']:.3f}, 저장 {m['loglik']:.3f}, 같은 해에 도달한 초기값 {fit['n_replicated']}/12")
check('재추정', '다시 적합한 전이확률·응답확률·상태 비중 = 저장된 값', d_par < 2e-3, f'최대 차이 {d_par:.1e}')

# ── 6. 우도의 전수 열거 ──────────────────────────────────────────────────
rng = np.random.default_rng(2026)
pick = rng.choice(len(ids), 300, replace=False)
Ys = Y[pick]
Ms = (~np.isnan(Ys)).astype(float)
Y0 = np.nan_to_num(Ys)
eng = L.estep(Y0 * Ms, (1 - Y0) * Ms, fit['pi'], fit['A'], fit['theta'])['ind_loglik']
brute = np.empty(300)
paths = list(itertools.product(range(3), repeat=6))
for i in range(300):
    tot = 0.0
    for z in paths:
        p = fit['pi'][z[0]]
        for t in range(1, 6):
            p *= fit['A'][t - 1, z[t - 1], z[t]]
        for t in range(6):
            for j in range(4):
                if Ms[i, t, j]:
                    q = fit['theta'][t, j, z[t]]
                    p *= q if Ys[i, t, j] == 1 else 1 - q
        tot += p
    brute[i] = np.log(tot)
check('우도', '엔진의 개인별 로그우도 = 729개 잠재경로 전수 열거(무작위 300명)', np.abs(eng - brute).max() < 1e-9, f'최대 차이 {np.abs(eng - brute).max():.1e}')

# ── 7. 모형이 함의하는 비율과 관측 비율 ──────────────────────────────────
occ_f = L.state_occupancy(fit['pi'], fit['A'])
implied = np.einsum('tk,tjk->tj', occ_f, fit['theta'])
obs = np.array([[np.average(Y[~np.isnan(Y[:, t, j]), t, j], weights=W[~np.isnan(Y[:, t, j])]) if (~np.isnan(Y[:, t, j])).any() else np.nan
                 for j in range(4)] for t in range(6)])
gapm = 100 * (implied - obs)
t_, j_ = np.unravel_index(np.nanargmax(np.abs(gapm)), gapm.shape)
pd.DataFrame([dict(wave=WAVES[t], item=ITEMS[j], implied_pct=100 * implied[t, j], observed_pct=100 * obs[t, j], diff_pp=gapm[t, j])
              for t in range(6) for j in range(4) if not np.isnan(obs[t, j])]).to_csv(os.path.join(OUT, 'real_marginal_fit.csv'), index=False, encoding='utf-8-sig')
# 이 항목은 자료나 계산의 오류를 가리는 검사가 아니라 모형이 자료를 얼마나 잘 맞추는지를 보는 진단이다.
# 응답확률을 여러 해에 걸쳐 같게 두므로 해마다의 비율이 정확히 맞지는 않는다.
res.append(dict(group='적합(참고)', check='모형이 함의하는 연도별 지표 비율과 관측 비율의 차이', result='진단',
                detail=f'평균 {np.nanmean(np.abs(gapm)):.2f}%포인트, 최대 {np.nanmax(np.abs(gapm)):.2f}%포인트({WAVES[t_]}년 {ITEMS[j_]})'))

# ── 8. 관측 전이율 ───────────────────────────────────────────────────────
man = {(r['item'], r['interval']): r for r in rs['manifest']}
worst = 0.0
for a, b in zip(WAVES[:-1], WAVES[1:]):
    pa = panel[panel.wave == a][['id', 'inapp_item', 'wt']].merge(panel[panel.wave == b][['id', 'inapp_item']], on='id', suffixes=('', '_next'))
    buy = pa[pa.inapp_item == 1]
    worst = max(worst, abs((buy.wt * buy.inapp_item_next).sum() / buy.wt.sum() - man[('inapp_item', f'{a}→{b}')]['persist']))
check('관측 전이율', '앱 내 아이템 구입 지속률을 두 해 자료의 결합으로 다시 계산', worst < 1e-9, f'최대 차이 {worst:.1e}')

out = pd.DataFrame(res)
out.to_csv(os.path.join(OUT, 'real_verification.csv'), index=False, encoding='utf-8-sig')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 90)
print(out.to_string())
print('검사 항목 모두 일치' if (out.result != '불일치').all() else '불일치 있음')
