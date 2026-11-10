# -*- coding: utf-8 -*-
"""
06_covariate_lta.py — 규제 강도 변인을 공변량으로 넣은 잠재전이분석

변인
  주 변인    개인별 가격 인상 노출 지수(표준화). 기준 시점에 이용한 서비스 유형 × 그 유형의 2022년 인앱 가격 인상률.
  보조 변인  스마트폰 운영체제(안드로이드 = 1).
  시기 통제  정책 단계. 전이 절편을 구간마다 자유롭게 두어 모든 사람에게 공통인 시기 효과를 흡수하고,
             공변량 계수는 정책 단계로 나눈 앞 국면과 뒤 국면에서 따로 추정한다.
  관심 모수  뒤 국면 계수 − 앞 국면 계수(국면 × 노출 상호작용).
             노출이 큰 사람일수록 규제·가격 인상 이후 하향 전이가 더 늘었는가를 뜻한다.

자료
  기본은 모의패널이다(개인 원자료 미확보). 서비스 유형별 인상률만 실제 공개자료에서 읽는다.
  data/private/consumer_panel.csv 와 consumer_covariates.csv 가 있으면 --real 로 같은 모형을 실제 자료에 적합한다.

실행: python code/06_covariate_lta.py  [--quick] [--reps 60] [--real]
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.optimize import fsolve

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lta_engine as L            # noqa: E402
import lta_covariates as C        # noqa: E402
import regulation_exposure as RX  # noqa: E402
import study_design as D          # noqa: E402

QUICK = '--quick' in sys.argv
REAL = '--real' in sys.argv
REPS = int(sys.argv[sys.argv.index('--reps') + 1]) if '--reps' in sys.argv else (6 if QUICK else 60)
OUT, FIG = os.path.join(ROOT, 'outputs'), os.path.join(ROOT, 'figures')
K, J, T = 3, 4, len(D.WAVES)
SL = D.STATE_LABELS
COV_NAMES = ['가격 인상 노출 지수(z)', '안드로이드']
B_MAIN = RX.coef_groups(D.WAVES, cut=2)        # [0,0,1,1]
B_SENS = RX.coef_groups(D.WAVES, cut=1)        # [0,1,1,1]
RATES = RX.sector_price_increase()

# ---------------------------------------------------------------------------
# 1. 모의패널의 설계(가정). 실제 자료 모드에서는 쓰지 않는다.
# ---------------------------------------------------------------------------
USE_BASE = dict(video=0.45, music=0.25, webtoon=0.25, game=0.20)   # 기준 시점 서비스 유형별 이용률(가정)
P_ANDROID = 0.72                                                   # 안드로이드 비중(가정)
G_EXPO = np.array([0.0, 0.8, 1.3])      # 초기 상태 로짓: 노출 지수 1SD 의 효과(S1 기준)
G_AND = np.array([0.0, 0.0, 0.0])
POST_EFFECTS = {                         # 뒤 국면에서만 나타나는 공변량 효과(로그 오즈, 머무름 대비)
    (2, 1, 0): 0.50,                     # 복합 구매 → 구독 중심, 노출 지수 1SD
    (2, 0, 0): 0.30,                     # 복합 구매 → 저소비, 노출 지수 1SD
    (1, 0, 0): 0.25,                     # 구독 중심 → 저소비, 노출 지수 1SD
    (2, 1, 1): 0.30,                     # 복합 구매 → 구독 중심, 안드로이드
}


def make_covariates(n, rng):
    u = rng.normal(size=n)                                         # 디지털 콘텐츠 이용 성향(서비스 간 상관)
    use = np.column_stack([(rng.random(n) < 1 / (1 + np.exp(-(np.log(p / (1 - p)) + 0.8 * u)))).astype(float)
                           for p in USE_BASE.values()])
    ex = RX.exposure_index(use, RATES)
    android = (rng.random(n) < P_ANDROID).astype(float)
    return np.column_stack([ex['z'], android]), ex, use


def true_parameters(X, effects=POST_EFFECTS, b_groups=B_MAIN):
    """설계 참값: 응답확률은 study_design, 전이 절편은 A_BASE(구간 공통), 공변량 효과는 뒤 국면에만."""
    n = X.shape[0]
    Z, info = C.design_trans(X, n, T, b_groups=b_groups)
    G, P = info['G'], info['P']
    W = np.zeros((K, Z.shape[2], K))
    for a in range(K):
        W[a, :G, :] = np.log(D.A_BASE[a] / D.A_BASE[a, a])
    for (a, b, p), val in effects.items():
        W[a, G + 1 * P + p, b] = val
    X0d = C.design_init(X, n)

    def gap(c):
        Gam = np.zeros((3, K)); Gam[0, 1:] = c; Gam[1] = G_EXPO; Gam[2] = G_AND
        return C._softmax(X0d @ Gam).mean(0)[1:] - D.PI0[1:]
    c = fsolve(gap, np.log(D.PI0[1:] / D.PI0[0]))
    Gam = np.zeros((3, K)); Gam[0, 1:] = c; Gam[1] = G_EXPO; Gam[2] = G_AND
    return D.THETA.copy(), Gam, W, info


def common_start(theta, Gam, W, info):
    """국면별 계수 모형의 값 → 공통 계수 모형(H=1)의 시작값(두 국면 계수의 평균)."""
    G, P, H = info['G'], info['P'], info['H']
    Wc = np.zeros((K, G + P, K))
    Wc[:, :G] = W[:, :G]
    Wc[:, G:] = W[:, G:].reshape(K, H, P, K).mean(1)
    return theta, Gam, Wc


def interaction_wald(fit, a, b, p):
    return C.wald_contrast(fit, {C.find_param(fit, 'trans', a, b, p, 1): 1.0, C.find_param(fit, 'trans', a, b, p, 0): -1.0})


# ---------------------------------------------------------------------------
# 2. 자료
# ---------------------------------------------------------------------------
rng = np.random.default_rng(20261111)
if REAL:
    panel = pd.read_csv(os.path.join(ROOT, 'data', 'private', 'consumer_panel.csv'))
    cov = pd.read_csv(os.path.join(ROOT, 'data', 'private', 'consumer_covariates.csv'))
    keep = set(cov.dropna()['id'])
    panel = panel[panel['id'].isin(keep)]
    Y, ids = L.panel_to_array(panel, 'id', 'wave', D.ITEMS, D.WAVES)
    X, EX = RX.build_covariates(cov, RATES, id_order=ids)
    truth = None
else:
    X, EX, USE = make_covariates(D.N_DESIGN, rng)
    TH, GAM, W_TRUE, INFO_T = true_parameters(X)
    truth = (TH, GAM, W_TRUE)
    Y, S, _ = C.simulate_panel_cov(TH, GAM, W_TRUE, X, X, T, rng, b_groups=B_MAIN, retention=D.RETENTION,
                                   reentry=D.REENTRY, item_missing=D.ITEM_MISSING)
N = Y.shape[0]

# ---------------------------------------------------------------------------
# 3. 모형 적합: M0 공변량 없음 → M1 공통 계수 → M2 국면별 계수(주 사양) → M2s 경계를 앞당긴 민감도 사양
# ---------------------------------------------------------------------------
t0 = time.time()
st = 4 if QUICK else 10
m0 = L.fit(Y, K, n_starts=st, n_jobs=-2)
m1 = C.fit_cov(Y, K, X_init=X, X_trans=X, base=m0, se=False)
m2 = C.fit_cov(Y, K, X_init=X, X_trans=X, b_groups=B_MAIN, base=m0)
m2s = C.fit_cov(Y, K, X_init=X, X_trans=X, b_groups=B_SENS, base=m0)
fit_sec = time.time() - t0
models = pd.DataFrame([
    dict(model='M0 공변량 없음(구간별 절편)', loglik=m0['loglik'], npar=m0['npar'], bic=m0['bic']),
    dict(model='M1 공변량, 계수 공통', loglik=m1['loglik'], npar=m1['npar'], bic=m1['bic']),
    dict(model='M2 공변량, 국면별 계수 [0,0,1,1]', loglik=m2['loglik'], npar=m2['npar'], bic=m2['bic']),
    dict(model='M2s 공변량, 국면별 계수 [0,1,1,1]', loglik=m2s['loglik'], npar=m2s['npar'], bic=m2s['bic']),
])
lr_cov = L.lr_test(m0, m1)             # 공변량 전체(초기 + 전이)
lr_int = L.lr_test(m1, m2)             # 국면 × 공변량 상호작용(전이 계수 12개)
lr_int_s = L.lr_test(m1, m2s)

coef = C.coef_table(m2, COV_NAMES, COV_NAMES, SL)
if truth is not None:
    coef['true'] = C._pack(*truth)
    coef['covered95'] = (coef['estimate'] - 1.96 * coef['se'] <= coef['true']) & (coef['true'] <= coef['estimate'] + 1.96 * coef['se'])

inter = []
for a in range(K):
    for b in range(K):
        if a == b:
            continue
        for p in range(len(COV_NAMES)):
            wtest = interaction_wald(m2, a, b, p)
            inter.append(dict(origin=SL[a], dest=SL[b], covariate=COV_NAMES[p], **wtest,
                              true=(POST_EFFECTS.get((a, b, p), 0.0) if truth is not None else np.nan)))
inter = pd.DataFrame(inter)

# 노출 지수 수준별 예측 전이확률(안드로이드 = 1, 국면 내 구간 평균)
grid = np.linspace(-1.5, 2.0, 36)


def curve(Wm, info, a, b, regime, b_groups):
    f = dict(W=Wm, info=info, D=Wm.shape[1])
    ts = [t for t in range(T - 1) if b_groups[t] == regime]
    return np.array([np.mean([C.predict_transition(f, [x, 1.0], regime, t)[a, b] for t in ts]) for x in grid])


pred = []
for (a, b) in [(2, 1), (2, 0), (1, 0)]:
    for reg, name in [(0, '앞 국면'), (1, '뒤 국면')]:
        est = curve(m2['W'], m2['info'], a, b, reg, B_MAIN)
        tru = curve(W_TRUE, INFO_T, a, b, reg, B_MAIN) if truth is not None else np.full(len(grid), np.nan)
        pred += [dict(origin=SL[a], dest=SL[b], regime=name, exposure_z=x, estimate=e, true=t) for x, e, t in zip(grid, est, tru)]
pred = pd.DataFrame(pred)

# ---------------------------------------------------------------------------
# 4. 소규모 몬테카를로: 상호작용 검정의 크기와 검정력(모의자료 모드에서만)
# ---------------------------------------------------------------------------
def one_rep(n, rep, alt):
    r = np.random.default_rng([20261111, n, rep, int(alt)])
    Xr, _, _ = make_covariates(n, r)
    th, gm, wt, info = true_parameters(Xr, POST_EFFECTS if alt else {})
    Yr, _, _ = C.simulate_panel_cov(th, gm, wt, Xr, Xr, T, r, b_groups=B_MAIN, retention=D.RETENTION,
                                    reentry=D.REENTRY, item_missing=D.ITEM_MISSING)
    f2 = C.fit_cov(Yr, K, X_init=Xr, X_trans=Xr, b_groups=B_MAIN, init=(th, gm, wt), tol=1e-8, maxit=1500)
    f1 = C.fit_cov(Yr, K, X_init=Xr, X_trans=Xr, init=common_start(th, gm, wt, info), tol=1e-8, maxit=1500, se=False)
    wd = interaction_wald(f2, 2, 1, 0)
    return dict(N=n, alt=alt, rep=rep, lr_p=L.lr_test(f1, f2)['p'], wald_p=wd['p'], wald_est=wd['estimate'], wald_se=wd['se'],
                converged=bool(f1['converged'] and f2['converged']), info_pd=bool(f2['info_pd']))


mc_sum = None
if truth is not None and REPS > 0:
    from joblib import Parallel, delayed
    grid_mc = [(n, alt) for n in ((2000, D.N_DESIGN) if not QUICK else (D.N_DESIGN,)) for alt in (False, True)]
    res = Parallel(n_jobs=-2)(delayed(one_rep)(n, i, alt) for (n, alt) in grid_mc for i in range(REPS))
    mc = pd.DataFrame(res)
    mc.to_csv(os.path.join(OUT, 'cov_mc_replicates.csv'), index=False, encoding='utf-8-sig')
    mc_sum = mc.groupby(['N', 'alt']).apply(lambda d: pd.Series(dict(
        reps=len(d), lr_reject=(d.lr_p < 0.05).mean(), wald_reject=(d.wald_p < 0.05).mean(),
        wald_mean=d.wald_est.mean(), wald_sd=d.wald_est.std(), wald_se_mean=d.wald_se.mean(),
        pct_converged=100 * d.converged.mean()))).reset_index()
    mc_sum.to_csv(os.path.join(OUT, 'cov_mc_summary.csv'), index=False, encoding='utf-8-sig')

# ---------------------------------------------------------------------------
# 5. 저장
# ---------------------------------------------------------------------------
models.to_csv(os.path.join(OUT, 'cov_model_comparison.csv'), index=False, encoding='utf-8-sig')
coef.to_csv(os.path.join(OUT, 'cov_coefficients.csv'), index=False, encoding='utf-8-sig')
inter.to_csv(os.path.join(OUT, 'cov_interaction_tests.csv'), index=False, encoding='utf-8-sig')
pred.to_csv(os.path.join(OUT, 'cov_predicted_transitions.csv'), index=False, encoding='utf-8-sig')
focus = inter[(inter.origin == SL[2]) & (inter.dest == SL[1]) & (inter.covariate == COV_NAMES[0])].iloc[0]
tr = coef[coef.part == 'trans']
summary = dict(
    data_mode='real' if REAL else 'synthetic', N=int(N), waves=D.WAVES, policy_stage={str(w): RX.policy_stage(w) for w in D.WAVES},
    coef_groups_main=B_MAIN, coef_groups_sensitivity=B_SENS,
    sector_price_increase_pct=RATES, exposure_raw_mean=EX['mean'], exposure_raw_sd=EX['sd'],
    android_share=float(X[:, 1].mean()), fit_seconds=round(fit_sec, 1),
    models=models.to_dict('records'), lr_covariates=lr_cov, lr_interaction=lr_int, lr_interaction_sensitivity=lr_int_s,
    focus_interaction=dict(origin=focus.origin, dest=focus.dest, covariate=focus.covariate, estimate=float(focus.estimate),
                           se=float(focus.se), z=float(focus.z), p=float(focus.p), true=float(focus['true'])),
    info_pd=bool(m2['info_pd']), iterations=int(m2['iterations']), converged=bool(m2['converged']),
    max_abs_err_theta=(float(np.abs(m2['theta_jk'] - truth[0]).max()) if truth is not None else None),
    trans_coef_coverage95=(float(tr.covered95.mean()) if truth is not None else None),
    trans_coef_max_abs_z_err=(float(((tr.estimate - tr['true']) / tr.se).abs().max()) if truth is not None else None),
    monte_carlo=(mc_sum.to_dict('records') if mc_sum is not None else None), mc_reps=REPS,
)
with open(os.path.join(OUT, 'cov_summary.json'), 'w', encoding='utf-8') as fh:
    json.dump(summary, fh, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# 6. 그림 11: 노출 지수에 따른 하향 전이확률, 국면별
# ---------------------------------------------------------------------------
import matplotlib                       # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt         # noqa: E402
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
BLUE, ORANGE, INK, MUTED, GRID = '#2a78d6', '#eb6834', '#1f2937', '#6b7280', '#e5e7eb'
panels = [(SL[2], SL[1], '복합 구매 → 구독 중심'), (SL[2], SL[0], '복합 구매 → 저소비'), (SL[1], SL[0], '구독 중심 → 저소비')]
fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.9))
for ax, (o, d, ttl) in zip(axes, panels):
    top = 0
    for name, col in [('앞 국면', BLUE), ('뒤 국면', ORANGE)]:
        q = pred[(pred.origin == o) & (pred.dest == d) & (pred.regime == name)]
        ax.plot(q.exposure_z, q.estimate, color=col, lw=2.2, label=f'{name} 추정')
        if truth is not None:
            ax.plot(q.exposure_z, q['true'], color=col, lw=1.3, ls=(0, (4, 3)), alpha=0.75, label=f'{name} 참값')
        top = max(top, q.estimate.max(), np.nanmax(q['true']) if truth is not None else 0)
    ax.set_title(ttl, fontsize=11, color=INK, loc='left', fontweight='bold')
    ax.set_ylim(0, top * 1.25)
    ax.set_xlabel('가격 인상 노출 지수(표준화)', fontsize=9, color=MUTED)
    ax.grid(axis='y', color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0, labelsize=9)
axes[0].set_ylabel('연간 전이확률', fontsize=9, color=MUTED)
h, lab = axes[0].get_legend_handles_labels()
fig.legend(h, lab, frameon=False, fontsize=9, loc='upper center', ncol=4, bbox_to_anchor=(0.5, 1.0))
note = '모의자료. 안드로이드 이용자 기준, 국면 내 두 구간의 평균. 앞 국면: 2020→21, 21→22 / 뒤 국면: 22→23, 23→24.' if truth is not None else '안드로이드 이용자 기준, 국면 내 구간 평균.'
fig.text(0.03, 0.015, note, fontsize=8, color=MUTED, va='bottom')
fig.subplots_adjust(left=0.07, right=0.985, top=0.80, bottom=0.2, wspace=0.22)
fig.savefig(os.path.join(FIG, 'fig11_covariate_transitions.png'), dpi=170)

pd.set_option('display.width', 220)
print(json.dumps({k: summary[k] for k in ('N', 'sector_price_increase_pct', 'exposure_raw_mean', 'exposure_raw_sd', 'fit_seconds', 'lr_covariates',
                                         'lr_interaction', 'lr_interaction_sensitivity', 'focus_interaction', 'info_pd', 'iterations',
                                         'max_abs_err_theta', 'trans_coef_coverage95', 'trans_coef_max_abs_z_err')}, ensure_ascii=False, indent=1))
print(models.to_string())
print(inter.round(3).to_string())
if mc_sum is not None:
    print(mc_sum.round(3).to_string())
