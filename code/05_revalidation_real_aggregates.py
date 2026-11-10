# -*- coding: utf-8 -*-
"""
05_revalidation_real_aggregates.py — 2021~2025년 공표 집계치로 잠재전이분석 설계를 재검증

무엇을 하는가
  A. 2021~2025 한국미디어패널조사 보고서 5권에서 옮긴 연도별 경험률을 사례 수/분모 산술로 점검한다.
  B. 모의패널 설계(study_design.py)가 가정한 연도별 경험률과 실제 공표 수치를 대조한다.
  C. 실제 연도 간 변화의 크기를 두 비율 검정으로 요약한다(독립표본 근사, 설계효과 2 민감도).
  D. '측정 불변 + 3개 상태' 잠재 마코프 모형이 실제 집계 궤적을 재현할 수 있는지 최소 카이제곱으로 본다.
     (i) 전이 동질  (ii) 전이 구간별 자유.  집계 자료만으로는 모수가 식별되지 않으므로
     '가장 잘 맞춘 경우에도 남는 오차'만 해석한다.
  E. (ii)의 해로 실제 궤적을 따르는 모의패널(시나리오 B2)을 만들고 같은 엔진으로 다시 추정한다.
     동질성 검정, 상태 수 선택, 모수 복원, 소규모 몬테카를로 검정력.

주의: 개인 원자료가 아니므로 E의 수치는 여전히 모의자료 결과다. 실제 자료인 것은 A~D의 집계치뿐이다.
실행: python code/05_revalidation_real_aggregates.py  [--quick]
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, softmax
from scipy.stats import norm

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lta_engine as L          # noqa: E402
import study_design as D        # noqa: E402

QUICK = '--quick' in sys.argv
OUT, FIG, DATA = (os.path.join(ROOT, d) for d in ('outputs', 'figures', 'data'))
ITEMS = D.ITEMS
YEARS = [2021, 2022, 2023, 2024, 2025]

# ---------------------------------------------------------------------------
# A. 실제 공표 수치 (보고서별 표 번호와 PDF 쪽수)
# ---------------------------------------------------------------------------
SRC = {
    2021: dict(report='2021 한국미디어패널조사', app='<표 4-66> PDF 194쪽', ott='<표 4-70> PDF 216쪽', content='<표 4-71> PDF 217쪽'),
    2022: dict(report='2022 한국미디어패널조사', app='<표 4-43> PDF 125쪽', ott='<표 4-42> PDF 124쪽', content='<표 4-44> PDF 125쪽'),
    2023: dict(report='2023 한국미디어패널조사', app='<표 4-54> PDF 125쪽', ott='<표 4-53> PDF 124쪽', content='<표 4-55> PDF 125쪽'),
    2024: dict(report='2024 한국미디어패널조사', app='<표 4-55> PDF 135쪽', ott='<표 4-54> PDF 134쪽', content='<표 4-56> PDF 135쪽'),
    2025: dict(report='2025 한국미디어패널조사', app='<표 4-44> PDF 127쪽', ott='<표 4-43> PDF 126쪽', content='<표 4-45> PDF 127쪽'),
}
REAL = pd.DataFrame(dict(
    year=YEARS,
    respondents=[10154, 9941, 9757, 8693, 8411],
    smart_users=[9623, 9560, 9386, 8439, 8178],
    paid_app_n=[701, 403, 377, 552, 439], paid_app_pct=[7.3, 4.2, 4.0, 6.5, 5.4],
    inapp_n=[1356, 787, 546, 1199, 1261], inapp_pct=[14.1, 8.2, 5.8, 14.2, 15.4],
    any_app_n=[1534, 904, 708, 1450, 1410],
    ott_users=[8294, 8487, 8595, 7756, 7648], ott_use_pct=[81.7, 85.4, 88.1, 89.2, 90.9],
    svod_n=[1718, 2282, 2603, 4211, 4564], svod_pct=[20.7, 26.9, 30.3, 54.3, 59.7],
    music_n=[3939, 3623, 3205, 2630, 2355], music_pct=[38.8, 36.4, 32.9, 30.3, 28.0],
    game_n=[3144, 2155, 1873, 1635, 1412], game_pct=[31.0, 21.7, 19.2, 18.8, 16.8],
))
# 분모가 서로 다른 공표 경험률과 사례 수의 산술 일치 점검
CHECKS = [('paid_app', 'paid_app_n', 'smart_users', 'paid_app_pct'), ('inapp_item', 'inapp_n', 'smart_users', 'inapp_pct'),
          ('ott_svod', 'svod_n', 'ott_users', 'svod_pct'), ('ott_use', 'ott_users', 'respondents', 'ott_use_pct'),
          ('music_use', 'music_n', 'respondents', 'music_pct'), ('game_use', 'game_n', 'respondents', 'game_pct')]
rows = []
for name, k, base, pct in CHECKS:
    for _, r in REAL.iterrows():
        calc = 100 * r[k] / r[base]
        rows.append(dict(indicator=name, year=int(r.year), n=int(r[k]), base=int(r[base]), published_pct=r[pct],
                         recomputed_pct=round(calc, 2), abs_diff=round(abs(calc - r[pct]), 2), ok=abs(calc - r[pct]) <= 0.06))
check = pd.DataFrame(rows)

# 잠재전이분석 지표 정의(전체 응답자 기준 비율)로 환산
N = REAL.respondents.values.astype(float)
OBS = np.column_stack([REAL.paid_app_n / N, REAL.inapp_n / N, REAL.svod_n / N, REAL.music_n / N])   # (5년, 4문항)
series = pd.DataFrame(100 * OBS, columns=ITEMS)
series.insert(0, 'year', YEARS)
series.insert(1, 'respondents', REAL.respondents)
series['note_paid_video'] = '월정액(SVOD) 가입자 / 전체 응답자. 2021년은 최근 3개월, 2022년부터 지난 1년 기준'
series['note_paid_music'] = '온라인 음악 이용률(무료 이용 포함, 유료 이용의 상한)'

# ---------------------------------------------------------------------------
# B. 모의패널 설계와의 대조
# ---------------------------------------------------------------------------
design = pd.read_csv(os.path.join(OUT, 'observed_prevalence_by_wave.csv'), index_col=0)
cmp_rows = []
for y in YEARS:
    for j, it in enumerate(ITEMS):
        d = design.loc[y, it] if y in design.index else np.nan
        cmp_rows.append(dict(year=y, item=it, real_pct=round(100 * OBS[YEARS.index(y), j], 2),
                             design_pct=d, diff_pp=round(d - 100 * OBS[YEARS.index(y), j], 2) if d == d else np.nan))
compare = pd.DataFrame(cmp_rows)

# ---------------------------------------------------------------------------
# C. 연도 간 변화(두 비율 z 검정; 패널 중복을 무시한 독립표본 근사)
# ---------------------------------------------------------------------------
chg = []
for j, it in enumerate(ITEMS):
    for t in range(1, 5):
        p0, p1, n0, n1 = OBS[t - 1, j], OBS[t, j], N[t - 1], N[t]
        se = np.sqrt(p0 * (1 - p0) / n0 + p1 * (1 - p1) / n1)
        z = (p1 - p0) / se
        chg.append(dict(item=it, interval=f'{YEARS[t - 1]}→{YEARS[t]}', change_pp=round(100 * (p1 - p0), 2),
                        relative_pct=round(100 * (p1 / p0 - 1), 1), z=round(z, 2), p=float(2 * norm.sf(abs(z))),
                        z_deff2=round(z / np.sqrt(2), 2), p_deff2=float(2 * norm.sf(abs(z) / np.sqrt(2)))))
changes = pd.DataFrame(chg)

# ---------------------------------------------------------------------------
# D. 집계 수준의 모형 정합성: 최소 카이제곱
# ---------------------------------------------------------------------------
K, T, J = 3, 5, 4


def _chi(pred):
    pred = np.clip(pred, 1e-6, 1 - 1e-6)
    return float((N[:, None] * (OBS - pred) ** 2 / (pred * (1 - pred))).sum())


def pred_hom(x):
    th = expit(x[:J * K]).reshape(J, K)
    pi = softmax(x[J * K:J * K + K])
    A = softmax(x[J * K + K:].reshape(K, K), axis=1)
    occ = L.state_occupancy(pi, np.repeat(A[None], T - 1, axis=0))
    return occ @ th.T, th, occ, A


def pred_free(x):
    th = expit(x[:J * K]).reshape(J, K)
    occ = softmax(x[J * K:].reshape(T, K), axis=1)
    return occ @ th.T, th, occ, None


def best_fit(pred_fn, npar, n_starts, seed):
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(n_starts):
        x0 = rng.normal(0, 1.5, npar)
        r = minimize(lambda x: _chi(pred_fn(x)[0]), x0, method='L-BFGS-B', options=dict(maxiter=4000, maxfun=200000))
        if best is None or r.fun < best.fun:
            best = r
    return best


ns = 12 if QUICK else 80
r_hom = best_fit(pred_hom, J * K + K + K * K, ns, 11)
r_free = best_fit(pred_free, J * K + T * K, ns, 12)
P_hom, _, _, _ = pred_hom(r_hom.x)
P_free, _, _, _ = pred_free(r_free.x)
resid_hom, resid_free = 100 * (P_hom - OBS), 100 * (P_free - OBS)

# (iii) 해석 가능한 해: 집계 자료만으로는 응답확률이 식별되지 않으므로, 설계의 상태 프로파일(저소비·구독 중심·
#       복합 구매)에 가까운 해를 벌점으로 고른다. 시나리오 B2는 이 해를 참값으로 쓴다.
LAM = 400.0
rng_a = np.random.default_rng(13)
r_anc = None
for _ in range(ns):
    x0 = np.concatenate([np.log(D.THETA / (1 - D.THETA)).ravel() + rng_a.normal(0, 0.3, J * K), rng_a.normal(0, 1.0, T * K)])
    r = minimize(lambda x: _chi(pred_free(x)[0]) + LAM * ((pred_free(x)[1] - D.THETA) ** 2).sum(), x0,
                 method='L-BFGS-B', options=dict(maxiter=4000, maxfun=200000))
    if r_anc is None or r.fun < r_anc.fun:
        r_anc = r
P_anc, TH2, OCC2, _ = pred_free(r_anc.x)
resid_anc = 100 * (P_anc - OBS)
se_pp = 100 * np.sqrt(OBS * (1 - OBS) / N[:, None])     # 표본오차(%p)

# ---------------------------------------------------------------------------
# E. 실제 궤적을 따르는 모의패널(시나리오 B2)로 재추정
# ---------------------------------------------------------------------------
def closest_transition(d0, d1, base):
    """d0 @ A = d1 을 만족하면서 기준 전이행렬에 가장 가까운 확률행렬."""
    cons = [dict(type='eq', fun=lambda a: a.reshape(K, K).sum(1) - 1),
            dict(type='eq', fun=lambda a: d0 @ a.reshape(K, K) - d1)]
    x0 = (0.5 * base + 0.5 * np.repeat(d1[None], K, axis=0)).ravel()
    r = minimize(lambda a: ((a - base.ravel()) ** 2).sum(), x0, method='SLSQP', bounds=[(0, 1)] * (K * K),
                 constraints=cons, options=dict(maxiter=500, ftol=1e-12))
    A = np.clip(r.x.reshape(K, K), 0, None)
    return A / A.sum(1, keepdims=True)


A2 = np.array([closest_transition(OCC2[t], OCC2[t + 1], D.A_BASE) for t in range(T - 1)])
PI2 = OCC2[0]
RET2 = np.array([0.945, 0.948, 0.848, 0.921])       # 2022~2025년 공표 유지율(통합패널)
N2 = 10154                                          # 2021년 개인 응답자 수
rng = np.random.default_rng(20261110)
Y2, Z2, _ = L.simulate_panel(N2, PI2, A2, TH2, rng, retention=RET2, reentry=D.REENTRY, item_missing=D.ITEM_MISSING)
sim_prev = 100 * np.nanmean(Y2, axis=0)

st = 4 if QUICK else 8
het = L.fit(Y2, 3, n_starts=st, n_jobs=-2)
hom = L.fit(Y2, 3, n_starts=st, homog=True, n_jobs=-2)
lr = L.lr_test(hom, het)
n_obs = Y2.shape[0]
bic = {}
for k in (2, 3, 4):
    f = het if k == 3 else L.fit(Y2, k, n_starts=st, n_jobs=-2, maxit=1500, tol=1e-8)
    bic[k] = dict(loglik=f['loglik'], npar=int(f['npar']), bic=float(-2 * f['loglik'] + f['npar'] * np.log(n_obs)))
err_theta = float(np.abs(het['theta'][0] - TH2).max())
err_A = float(np.abs(het['A'] - A2).max())
ident = OCC2[:-1] >= 0.05                           # 출발 상태 비중이 5% 이상인 행만(그 미만은 전이확률이 사실상 식별되지 않음)
err_A_ident = float(np.abs(het['A'] - A2)[ident].max())


def one_rep(n, rep):
    r = np.random.default_rng([20261110, n, rep])
    Y, _, _ = L.simulate_panel(n, PI2, A2, TH2, r, retention=RET2, reentry=D.REENTRY, item_missing=D.ITEM_MISSING)
    truth = (PI2, A2, np.repeat(TH2[None], T, axis=0))
    s = int(r.integers(1, 2 ** 31 - 1))
    h1 = L.fit(Y, 3, n_starts=2, init=truth, seed=s, maxit=1500, tol=1e-8)
    h0 = L.fit(Y, 3, n_starts=2, homog=True, init=truth, seed=s, maxit=1500, tol=1e-8)
    return L.lr_test(h0, h1)['p']


from joblib import Parallel, delayed   # noqa: E402
reps = 4 if QUICK else 60
power = {}
for n in (500, 2000, 10154):
    ps = Parallel(n_jobs=-2)(delayed(one_rep)(n, i) for i in range(reps))
    power[n] = dict(reps=reps, reject_rate=float(np.mean(np.array(ps) < 0.05)))

# ---------------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------------
src_rows = []
for y in YEARS:
    r = REAL[REAL.year == y].iloc[0]
    for ind, k, base, pct, key, bname in [
            ('paid_app', 'paid_app_n', 'smart_users', 'paid_app_pct', 'app', '스마트 기기 이용자'),
            ('inapp_item', 'inapp_n', 'smart_users', 'inapp_pct', 'app', '스마트 기기 이용자'),
            ('ott_svod', 'svod_n', 'ott_users', 'svod_pct', 'ott', 'OTT 서비스 이용자'),
            ('music_use', 'music_n', 'respondents', 'music_pct', 'content', '전체 개인 응답자'),
            ('game_use', 'game_n', 'respondents', 'game_pct', 'content', '전체 개인 응답자')]:
        src_rows.append(dict(year=y, indicator=ind, base=bname, base_n=int(r[base]), n_experienced=int(r[k]),
                             published_pct=r[pct], source=f"정보통신정책연구원. {SRC[y]['report']}, {SRC[y][key]}"))
pd.DataFrame(src_rows).to_csv(os.path.join(DATA, 'kisdi_published_series_2021_2025.csv'), index=False, encoding='utf-8-sig')
check.to_csv(os.path.join(OUT, 'reval_arithmetic_check.csv'), index=False, encoding='utf-8-sig')
series.to_csv(os.path.join(OUT, 'reval_real_series.csv'), index=False, encoding='utf-8-sig')
compare.to_csv(os.path.join(OUT, 'reval_design_vs_real.csv'), index=False, encoding='utf-8-sig')
changes.to_csv(os.path.join(OUT, 'reval_yearly_changes.csv'), index=False, encoding='utf-8-sig')

summary = dict(
    arithmetic_checks=dict(n=int(len(check)), n_ok=int(check.ok.sum()), max_abs_diff=float(check.abs_diff.max())),
    real_series_pct={it: [round(v, 4) for v in 100 * OBS[:, j]] for j, it in enumerate(ITEMS)},   # 소수 넷째 자리까지(표시 단계의 반올림 오차 방지)
    design_series_pct={it: design[it].round(2).tolist() for it in ITEMS}, design_years=design.index.tolist(),
    design_vs_real_max_abs_diff_pp=float(compare.diff_pp.abs().max()),
    aggregate_fit=dict(
        homogeneous=dict(chi2=float(r_hom.fun), max_abs_resid_pp=float(np.abs(resid_hom).max()), rmse_pp=float(np.sqrt((resid_hom ** 2).mean()))),
        free_transitions=dict(chi2=float(r_free.fun), max_abs_resid_pp=float(np.abs(resid_free).max()), rmse_pp=float(np.sqrt((resid_free ** 2).mean()))),
        anchored_to_design_profiles=dict(chi2=_chi(P_anc), max_abs_resid_pp=float(np.abs(resid_anc).max()), rmse_pp=float(np.sqrt((resid_anc ** 2).mean())),
                                         theta_shift_from_design=(TH2 - D.THETA).round(3).tolist()),
        typical_sampling_se_pp=float(se_pp.mean()), n_cells=int(OBS.size)),
    scenario_b2=dict(
        theta=TH2.round(3).tolist(), occupancy=OCC2.round(3).tolist(), A=A2.round(3).tolist(), N=N2, retention=RET2.tolist(),
        simulated_prevalence_pct=sim_prev.round(2).tolist(), lr_homogeneity=lr, bic=bic,
        K_selected=int(min(bic, key=lambda k: bic[k]['bic'])), max_abs_err_theta=err_theta, max_abs_err_A=err_A, max_abs_err_A_rows_occ_ge_5pct=err_A_ident,
        n_replicated_best=int(het['n_replicated']), power_omnibus=power),
)
with open(os.path.join(OUT, 'reval_summary.json'), 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# 그림 10: 실제 공표 수치와 모의패널 설계
# ---------------------------------------------------------------------------
def draw_figure():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False
    BLUE, ORANGE, INK, MUTED, GRID = '#2a78d6', '#eb6834', '#1f2937', '#6b7280', '#e5e7eb'
    fig, axes = plt.subplots(2, 2, figsize=(9.2, 6.8), sharex=True)
    titles = {'paid_app': '유료 앱 구입', 'inapp_item': '앱 내 아이템 구입', 'paid_video': '영상(OTT) 월정액 이용', 'paid_music': '온라인 음악 이용'}
    for ax, (j, it) in zip(axes.ravel(), enumerate(ITEMS)):
        real = 100 * OBS[:, j]
        top = max(real.max(), design[it].max()) * 1.28
        ax.axvspan(2021.5, 2023.5, color='#f3f6fa', zorder=0)
        l1, = ax.plot(design.index, design[it], color=ORANGE, lw=2, marker='o', ms=5, label='모의패널 설계(가정)')
        l2, = ax.plot(YEARS, real, color=BLUE, lw=2, marker='o', ms=6, label='실제 공표 수치')
        for y, v in zip(YEARS, real):
            d = design.loc[y, it] if y in design.index else None
            below = d is not None and 0 <= d - v < 0.16 * top      # 설계선이 바로 위에 있으면 값 표시를 아래로
            ax.annotate(f'{v:.1f}', (y, v), textcoords='offset points', xytext=(0, -15 if below else 8), ha='center', fontsize=9, color=INK)
        ax.set_title(titles[it], fontsize=11.5, color=INK, loc='left', fontweight='bold')
        ax.set_ylim(0, top)
        ax.grid(axis='y', color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for s in ('top', 'right', 'left'):
            ax.spines[s].set_visible(False)
        ax.spines['bottom'].set_color(GRID)
        ax.tick_params(colors=MUTED, length=0, labelsize=9)
        ax.set_xticks(range(2020, 2026))
    for ax in axes[:, 0]:
        ax.set_ylabel('전체 응답자 대비 비율(%)', fontsize=9, color=MUTED)
    fig.legend(handles=[l2, l1], frameon=False, fontsize=9.5, loc='upper center', ncol=2, bbox_to_anchor=(0.5, 0.995))
    fig.text(0.03, 0.012, '음영: 2022·2023년 조사(지난 1년 회상이 인앱결제 의무화와 가격 인상 시기를 포함). 영상의 2021년은 최근 3개월 기준, 음악은 무료 이용 포함.' + chr(10) +
             '자료: 정보통신정책연구원, 2021~2025 한국미디어패널조사 보고서의 사례 수와 응답자 수로 계산.', fontsize=8, color=MUTED, va='bottom')
    fig.subplots_adjust(left=0.08, right=0.98, top=0.90, bottom=0.14, wspace=0.16, hspace=0.24)
    fig.savefig(os.path.join(FIG, 'fig10_real_series_vs_design.png'), dpi=170)


draw_figure()
print(json.dumps({k: summary[k] for k in ('arithmetic_checks', 'design_vs_real_max_abs_diff_pp', 'aggregate_fit')}, ensure_ascii=False, indent=1))
print('B2', json.dumps({k: summary['scenario_b2'][k] for k in ('theta', 'occupancy', 'simulated_prevalence_pct', 'lr_homogeneity', 'bic', 'K_selected',
                                                              'max_abs_err_theta', 'max_abs_err_A', 'max_abs_err_A_rows_occ_ge_5pct', 'power_omnibus')}, ensure_ascii=False))
print(changes.to_string())
print(np.round(resid_anc, 2))
