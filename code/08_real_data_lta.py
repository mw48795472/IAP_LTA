# -*- coding: utf-8 -*-
"""
08_real_data_lta.py — 한국미디어패널 개인 원자료(2020~2025)에 대한 잠재전이분석

입력  data/private/consumer_panel.csv (07_build_real_panel.py 가 만든다)
출력  outputs/real_*.csv, outputs/real_summary.json, figures/fig12_real_states.png, fig13_real_transitions.png
      (모두 집계 결과이며 개인 단위 자료는 내보내지 않는다)

분석의 순서
  A. 관측 지표의 전이율(모형 없이): 같은 사람이 다음 해에도 구매하였는가
  B. 상태 수 선택(K = 1~5)과 측정불변성 비교
  C. 주 모형: K = 3, 영상 문항만 2024년부터 응답확률이 달라지도록 둔 부분 측정불변, 구간별 자유 전이, 가중 추정
  D. 가구 단위 군집 부트스트랩으로 구간추정(상태 비중, 전이확률, 국면 간 차이)
  E. 전이 동질성의 우도비 검정(비가중, 모형 기반)
  F. 민감도: 완전 측정불변, K = 4, 2021~2025년만, 비대상을 결측으로, 비가중, 영상을 가입 여부로 정의
  G. 규제 강도 공변량 모형: 기준 시점(2020년) 가격 인상 노출 지수, 운영체제, 연령

사양에 관한 결정(자료를 본 뒤 정한 것이므로 탐색적이다)
  - 2020년 조사에는 OTT 지불 유형 문항이 없어 영상 지표는 2020년에 결측이다(우도에서 주변화).
  - 2024년에 영상 지표의 수준이 크게 달라졌다. 완전 측정불변 모형은 이를 모두 상태 이동으로 읽으므로,
    주 모형은 영상 문항의 응답확률만 2024년 전후로 따로 두었다. 나머지 세 문항이 상태의 뜻을 고정한다.
  - 가중치는 각 개인이 처음 응답한 해의 횡단 가중치(평균 1로 정규화)이다. 가중 추정에는 우도비 검정을 쓸 수 없으므로
    구간추정은 가구 군집 부트스트랩으로, 우도비 검정은 비가중 적합으로 따로 제시한다.

실행: python code/08_real_data_lta.py  [--quick]
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lta_engine as L            # noqa: E402
import lta_covariates as C        # noqa: E402
import regulation_exposure as RX  # noqa: E402

QUICK = '--quick' in sys.argv
OUT, FIG = os.path.join(ROOT, 'outputs'), os.path.join(ROOT, 'figures')
ITEMS = ['paid_app', 'inapp_item', 'paid_video', 'paid_music']
ITEM_KO = {'paid_app': '유료 앱 구입', 'inapp_item': '앱 내 아이템 구입', 'paid_video': '영상 유료 이용', 'paid_music': '음악 유료 이용'}
WAVES = [2020, 2021, 2022, 2023, 2024, 2025]
IV = [f'{a}→{b}' for a, b in zip(WAVES[:-1], WAVES[1:])]
SL = ['S1 저소비', 'S2 구독 중심', 'S3 복합 구매']
SMOKE = '--smoke' in sys.argv                      # 코드 점검용: 초기값·부트스트랩·반복 수를 최소로
NS = 2 if SMOKE else (4 if QUICK else 10)
NBOOT = 4 if SMOKE else (40 if QUICK else 300)
COV_MAXIT = 30 if SMOKE else 800


def clean(o):
    """JSON 에 NaN 이 들어가지 않게 None 으로 바꾼다(자바스크립트의 JSON.parse 가 NaN 을 읽지 못한다)."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o
t_start = time.time()

panel = pd.read_csv(os.path.join(ROOT, 'data', 'private', 'consumer_panel.csv'))


def load(waves, items=ITEMS):
    sub = panel[panel.wave.isin(waves)]
    Y, ids = L.panel_to_array(sub, 'id', 'wave', items, waves)
    first = sub.sort_values('wave').groupby('id').first().loc[ids]
    w = first['wt'].to_numpy()
    return Y, ids, w / w.mean(), first['hid'].to_numpy()


def video_break(waves, items=(2,)):
    g = np.zeros((len(waves), len(ITEMS)), int)
    for j in items:
        g[waves.index(2024):, j] = 1
    return g


Y, IDS, W, HID = load(WAVES)
N, T, J = Y.shape
TG = video_break(WAVES)

# ---------------------------------------------------------------------------
# A. 관측 지표의 전이율(모형 없이)
# ---------------------------------------------------------------------------
wide_w = panel.pivot(index='id', columns='wave', values='wt')
wide_h = panel.sort_values('wave').groupby('id')['hid'].first()


def manifest(item):
    wide = panel.pivot(index='id', columns='wave', values=item)
    rows = []
    for a, b in zip(WAVES[:-1], WAVES[1:]):
        m = wide[a].notna() & wide[b].notna()
        d = pd.DataFrame(dict(x0=wide.loc[m, a], x1=wide.loc[m, b], w=wide_w.loc[m, a], h=wide_h[m[m].index]))
        if len(d) == 0:
            continue

        # 가구별 합계 네 개(구입자의 가중 구입 수와 가중 인원, 비구입자의 같은 값)만 있으면 비율과 그 부트스트랩을 계산할 수 있다.
        d['n1'], d['d1'] = d.w * d.x1 * (d.x0 == 1), d.w * (d.x0 == 1)
        d['n0'], d['d0'] = d.w * d.x1 * (d.x0 == 0), d.w * (d.x0 == 0)
        S = d.groupby('h')[['n1', 'd1', 'n0', 'd0']].sum().to_numpy()
        tot = S.sum(0)
        est = (tot[0] / tot[1], tot[2] / tot[3])
        rng = np.random.default_rng([20261111, a])
        cnt = rng.multinomial(len(S), np.full(len(S), 1.0 / len(S)), size=200 if QUICK else 2000)   # 가구 재표집 횟수
        B = cnt @ S
        bs = np.column_stack([B[:, 0] / B[:, 1], B[:, 2] / B[:, 3]])
        rows.append(dict(item=item, interval=f'{a}→{b}', n=int(len(d)), n_buyers=int((d.x0 == 1).sum()),
                         persist=est[0], persist_lo=np.nanpercentile(bs[:, 0], 2.5), persist_hi=np.nanpercentile(bs[:, 0], 97.5),
                         entry=est[1], entry_lo=np.nanpercentile(bs[:, 1], 2.5), entry_hi=np.nanpercentile(bs[:, 1], 97.5)))
    return rows


man = pd.DataFrame(sum((manifest(it) for it in ITEMS), []))
print('A done', round(time.time() - t_start), flush=True)
man.to_csv(os.path.join(OUT, 'real_manifest_transitions.csv'), index=False, encoding='utf-8-sig')

# ---------------------------------------------------------------------------
# B. 상태 수 선택과 측정불변성
# ---------------------------------------------------------------------------
sel, fitsK = [], {}
for K in (1, 2, 3, 4, 5):
    for name, kw in (('완전 측정불변', dict()), ('영상 문항 2024년 단절', dict(invariant=False, t_groups=TG))):
        f = L.fit(Y, K, n_starts=1 if K == 1 else NS, w=W, n_jobs=-2, maxit=2500, tol=1e-8, **kw)
        occ = L.state_occupancy(f['pi'], f['A'])
        sel.append(dict(K=K, measurement=name, loglik=f['loglik'], npar=int(f['npar']), bic=f['bic'], aic=f['aic'],
                        min_state_share=float(occ.min()), n_replicated=int(f['n_replicated']), n_starts=1 if K == 1 else NS, converged=bool(f['converged'])))
        fitsK[(K, name)] = f
sel = pd.DataFrame(sel)
sel.to_csv(os.path.join(OUT, 'real_model_selection.csv'), index=False, encoding='utf-8-sig')

inv = []
for name, kw in (('완전 측정불변', dict()), ('영상 문항만 2024년 단절', dict(invariant=False, t_groups=TG)),
                 ('영상·음악 문항 2024년 단절', dict(invariant=False, t_groups=video_break(WAVES, (2, 3)))),
                 ('네 문항 모두 2024년 단절', dict(invariant=False, t_groups=video_break(WAVES, (0, 1, 2, 3)))),
                 ('시점별 자유', dict(invariant=False))):
    f = fitsK[(3, '완전 측정불변')] if name == '완전 측정불변' else (fitsK[(3, '영상 문항 2024년 단절')] if name.startswith('영상 문항만') else
                                                        L.fit(Y, 3, n_starts=NS, w=W, n_jobs=-2, maxit=2500, tol=1e-8, **kw))
    inv.append(dict(measurement=name, loglik=f['loglik'], npar=int(f['npar']), bic=f['bic'], n_replicated=int(f['n_replicated'])))
inv = pd.DataFrame(inv)
inv.to_csv(os.path.join(OUT, 'real_measurement_invariance.csv'), index=False, encoding='utf-8-sig')
print('B done', round(time.time() - t_start), flush=True)

# ---------------------------------------------------------------------------
# C. 주 모형
# ---------------------------------------------------------------------------
main = fitsK[(3, '영상 문항 2024년 단절')]
occ_main = L.state_occupancy(main['pi'], main['A'])
cq = L.classification_quality(Y, main['gamma'])


def boot_one(b):
    rng = np.random.default_rng([20261111, 7, b])
    hs, inv_idx = np.unique(HID, return_inverse=True)
    cnt = rng.multinomial(len(hs), np.full(len(hs), 1.0 / len(hs)))
    wb = W * cnt[inv_idx]
    keep = wb > 0
    f = L.fit(Y[keep], 3, n_starts=1, w=wb[keep], invariant=False, t_groups=TG, init=(main['pi'], main['A'], main['theta']), maxit=1500, tol=1e-8)
    return dict(occ=L.state_occupancy(f['pi'], f['A']), A=f['A'], theta=f['theta'], ok=bool(f['converged']))


boots = Parallel(n_jobs=-2)(delayed(boot_one)(b) for b in range(NBOOT))
boots = [b for b in boots if b['ok']]
bA, bO, bT = np.array([b['A'] for b in boots]), np.array([b['occ'] for b in boots]), np.array([b['theta'] for b in boots])
ci = lambda x: (float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5)))   # noqa: E731

prof = []
for j, it in enumerate(ITEMS):
    for k in range(3):
        for per, t in (('2020~2023', 0), ('2024~2025', T - 1)):
            if per == '2024~2025' and it != 'paid_video':
                continue
            lo, hi = ci(bT[:, t, j, k])
            prof.append(dict(item=it, item_ko=ITEM_KO[it], state=SL[k], period=per if it == 'paid_video' else '전 기간', estimate=main['theta'][t, j, k], lo=lo, hi=hi))
prof = pd.DataFrame(prof)
prof.to_csv(os.path.join(OUT, 'real_response_profiles.csv'), index=False, encoding='utf-8-sig')

occ_rows = []
for t, y in enumerate(WAVES):
    for k in range(3):
        lo, hi = ci(bO[:, t, k])
        occ_rows.append(dict(wave=y, state=SL[k], estimate=occ_main[t, k], lo=lo, hi=hi))
occ_df = pd.DataFrame(occ_rows)
occ_df.to_csv(os.path.join(OUT, 'real_state_occupancy.csv'), index=False, encoding='utf-8-sig')

tr_rows = []
for t, iv in enumerate(IV):
    for a in range(3):
        for b in range(3):
            lo, hi = ci(bA[:, t, a, b])
            tr_rows.append(dict(interval=iv, from_state=SL[a], to_state=SL[b], estimate=main['A'][t, a, b], lo=lo, hi=hi))
tr_df = pd.DataFrame(tr_rows)
tr_df.to_csv(os.path.join(OUT, 'real_transition_probabilities.csv'), index=False, encoding='utf-8-sig')

# 국면 간 차이: 가격 인상기(2021→22, 2022→23) − 이전(2020→21), 가격 인상기 − 이후(2023→24, 2024→25)
PRE, HIKE, POST = [0], [1, 2], [3, 4]


def contrast(Aarr, a, b, g1, g0):
    return Aarr[..., g1, a, b].mean(-1) - Aarr[..., g0, a, b].mean(-1)


con = []
for label, (a, b) in (('복합 구매 → 구독 중심', (2, 1)), ('복합 구매 → 저소비', (2, 0)), ('복합 구매 유지', (2, 2)),
                      ('구독 중심 → 저소비', (1, 0)), ('구독 중심 → 복합 구매', (1, 2)), ('저소비 → 구독 중심', (0, 1))):
    for cname, g1, g0 in (('가격 인상기 − 이전', HIKE, PRE), ('가격 인상기 − 이후', HIKE, POST)):
        est = float(contrast(main['A'], a, b, g1, g0))
        bs = contrast(bA, a, b, g1, g0)
        lo, hi = ci(bs)
        con.append(dict(transition=label, contrast=cname, estimate=est, lo=lo, hi=hi, boot_share_positive=float((bs > 0).mean())))
con = pd.DataFrame(con)
con.to_csv(os.path.join(OUT, 'real_regime_contrasts.csv'), index=False, encoding='utf-8-sig')
print('C-D done', round(time.time() - t_start), flush=True)

# ---------------------------------------------------------------------------
# E. 전이 동질성 검정(비가중, 모형 기반)
# ---------------------------------------------------------------------------
kwu = dict(invariant=False, t_groups=TG, n_starts=NS, n_jobs=-2, maxit=2500, tol=1e-8)
u_het = L.fit(Y, 3, **kwu)
u_hom = L.fit(Y, 3, homog=True, **kwu)
REG = {'두 국면 [0,0,1,1,1] (사전 지정)': [0, 0, 1, 1, 1], '두 국면 [0,1,1,1,1] (경계를 앞당김)': [0, 1, 1, 1, 1],
       '세 국면 [0,1,1,2,2] (이전·가격 인상기·이후)': [0, 1, 1, 2, 2]}
tests = [dict(test='총괄: 동질 대 구간별 자유', **L.lr_test(u_hom, u_het), bic_restricted=u_hom['bic'], bic_full=u_het['bic'])]
u_reg = {}
for name, g in REG.items():
    u_reg[name] = L.fit(Y, 3, a_groups=g, **kwu)
    tests.append(dict(test=f'초점: 동질 대 {name}', **L.lr_test(u_hom, u_reg[name]), bic_restricted=u_hom['bic'], bic_full=u_reg[name]['bic']))
    tests.append(dict(test=f'잔여: {name} 대 구간별 자유', **L.lr_test(u_reg[name], u_het), bic_restricted=u_reg[name]['bic'], bic_full=u_het['bic']))
tests = pd.DataFrame(tests)
tests.to_csv(os.path.join(OUT, 'real_homogeneity_tests.csv'), index=False, encoding='utf-8-sig')
print('E done', round(time.time() - t_start), flush=True)

# ---------------------------------------------------------------------------
# F. 민감도
# ---------------------------------------------------------------------------
def key(f, waves, label):
    occ = L.state_occupancy(f['pi'], f['A'])
    k = int(np.argmax(f['theta'][0][1]))                 # 앱 내 아이템 구입 확률이 가장 높은 상태(앱 구매 상태)
    r = dict(spec=label, K=f['K'], app_state_theta=' / '.join(f'{v:.2f}' for v in f['theta'][0][:, k]), loglik=f['loglik'], npar=int(f['npar']), bic=f['bic'])
    for t, y in enumerate(waves):
        r[f'top_share_{y}'] = float(occ[t, k])
    for t, (a, b) in enumerate(zip(waves[:-1], waves[1:])):
        r[f'top_stay_{a}→{b}'] = float(f['A'][t, k, k])
    return r


sens = [key(main, WAVES, '주 모형: K=3, 영상 문항 단절, 가중'), key(fitsK[(3, '완전 측정불변')], WAVES, '완전 측정불변'),
        key(fitsK[(4, '영상 문항 2024년 단절')], WAVES, 'K=4(영상 문항 단절)'), key(u_het, WAVES, '비가중')]
W5 = WAVES[1:]
Y5, _, w5, _ = load(W5)
sens.append(key(L.fit(Y5, 3, w=w5, invariant=False, t_groups=video_break(W5), n_starts=NS, n_jobs=-2, maxit=2500, tol=1e-8), W5, '2021~2025년만'))
Yna, _, wna, _ = load(WAVES, ['paid_app_na', 'inapp_item_na', 'paid_video_na', 'paid_music'])
sens.append(key(L.fit(Yna, 3, w=wna, invariant=False, t_groups=TG, n_starts=NS, n_jobs=-2, maxit=2500, tol=1e-8), WAVES, '비대상을 결측으로'))
Ysub, _, wsub, _ = load(WAVES, ['paid_app', 'inapp_item', 'sub_video', 'paid_music'])
sens.append(key(L.fit(Ysub, 3, w=wsub, invariant=False, t_groups=TG, n_starts=NS, n_jobs=-2, maxit=2500, tol=1e-8), WAVES, '영상을 가입 여부로 정의'))
cc = ~np.isnan(Y[:, :, 0]).any(1)
sens.append(key(L.fit(Y[cc], 3, w=W[cc], invariant=False, t_groups=TG, n_starts=NS, n_jobs=-2, maxit=2500, tol=1e-8), WAVES, '여섯 해 모두 응답한 사람만'))
sens = pd.DataFrame(sens)
sens.to_csv(os.path.join(OUT, 'real_sensitivity.csv'), index=False, encoding='utf-8-sig')
print('F done', round(time.time() - t_start), flush=True)
k4 = fitsK[(4, '영상 문항 2024년 단절')]

# ---------------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------------
prev = pd.read_csv(os.path.join(OUT, 'real_prevalence_by_wave.csv'))
summary = dict(
    data_mode='real', n_persons=int(N), n_households=int(len(np.unique(HID))), n_person_waves=int((~np.isnan(Y[:, :, 0])).sum()),
    n_all_waves=int(cc.sum()), waves=WAVES, items=ITEMS, weights='first observed wave cross-sectional weight, normalised to mean 1',
    prevalence=prev.to_dict('records'),
    model_selection=sel.to_dict('records'), measurement_invariance=inv.to_dict('records'),
    main=dict(K=3, measurement='영상 문항만 2024년부터 응답확률을 따로 둠', loglik=main['loglik'], npar=int(main['npar']), bic=main['bic'],
              n_replicated=int(main['n_replicated']), theta_2020_2023=main['theta'][0].round(4).tolist(), theta_2024_2025=main['theta'][-1].round(4).tolist(),
              occupancy=occ_main.round(4).tolist(), A=main['A'].round(4).tolist(),
              classification=dict(mean_max_posterior=float(cq[0]), entropy=float(cq[1]))),
    bootstrap=dict(n_requested=NBOOT, n_valid=len(boots), unit='household'),
    contrasts=con.to_dict('records'), tests=tests.to_dict('records'), sensitivity=sens.to_dict('records'),
    k4=dict(theta_2020_2023=k4['theta'][0].round(4).tolist(), occupancy=L.state_occupancy(k4['pi'], k4['A']).round(4).tolist(), A=k4['A'].round(4).tolist()),
    manifest=man.to_dict('records'), covariate_model=None, seconds=round(time.time() - t_start, 1),
)
with open(os.path.join(OUT, 'real_summary.json'), 'w', encoding='utf-8') as fh:
    json.dump(clean(summary), fh, ensure_ascii=False, indent=1)

# ---------------------------------------------------------------------------
# 그림
# ---------------------------------------------------------------------------
import matplotlib                       # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt         # noqa: E402
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
BLUE, ORANGE, GREEN, INK, MUTED, GRID = '#2a78d6', '#eb6834', '#1baf7a', '#1f2937', '#6b7280', '#e5e7eb'
SC = [BLUE, GREEN, ORANGE]


def style(ax):
    ax.grid(axis='y', color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0, labelsize=9)


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.2, 4.2), gridspec_kw=dict(width_ratios=[1.15, 1]))
xl = ['유료 앱', '앱 내\n아이템', '영상\n(~2023)', '영상\n(2024~)', '음악']
cols = [('paid_app', 0), ('inapp_item', 0), ('paid_video', 0), ('paid_video', T - 1), ('paid_music', 0)]
for k in range(3):
    vals = [main['theta'][t, ITEMS.index(it), k] for it, t in cols]
    los = [np.percentile(bT[:, t, ITEMS.index(it), k], 2.5) for it, t in cols]
    his = [np.percentile(bT[:, t, ITEMS.index(it), k], 97.5) for it, t in cols]
    x = np.arange(5) + (k - 1) * 0.24
    ax1.bar(x, vals, width=0.22, color=SC[k], label=SL[k])
    ax1.errorbar(x, vals, yerr=[np.array(vals) - los, np.array(his) - vals], fmt='none', ecolor=INK, elinewidth=0.8, capsize=2)
ax1.set_xticks(range(5)); ax1.set_xticklabels(xl)
ax1.set_ylim(0, 1); ax1.set_ylabel('응답확률', fontsize=9, color=MUTED)
ax1.set_title('(가) 상태별 응답확률', fontsize=11, color=INK, loc='left', fontweight='bold')
ax1.legend(frameon=False, fontsize=9, ncol=3, loc='upper left', bbox_to_anchor=(0, 1.0))
style(ax1)
for k in range(3):
    ax2.fill_between(WAVES, np.percentile(bO[:, :, k], 2.5, axis=0), np.percentile(bO[:, :, k], 97.5, axis=0), color=SC[k], alpha=0.15, lw=0)
    ax2.plot(WAVES, occ_main[:, k], color=SC[k], lw=2, marker='o', ms=5)
    ax2.annotate(f'{SL[k][3:]} {100 * occ_main[-1, k]:.0f}%', (WAVES[-1], occ_main[-1, k]), textcoords='offset points', xytext=(6, -3), fontsize=9, color=INK)
ax2.axvspan(2021.5, 2023.5, color='#f3f6fa', zorder=0)
ax2.set_xlim(2019.8, 2026.6); ax2.set_ylim(0, 0.8); ax2.set_xticks(WAVES)
ax2.set_title('(나) 상태 비중의 추이', fontsize=11, color=INK, loc='left', fontweight='bold')
style(ax2)
fig.text(0.02, 0.012, f'한국미디어패널 개인 원자료 2020~2025년, {N:,}명. 가중 추정, 오차 표시는 가구 군집 부트스트랩 95% 구간. 음영은 2022·2023년 조사.', fontsize=8, color=MUTED, va='bottom')
fig.subplots_adjust(left=0.07, right=0.985, top=0.9, bottom=0.17, wspace=0.16)
fig.savefig(os.path.join(FIG, 'fig12_real_states.png'), dpi=170)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.2, 4.2))
x = np.arange(len(IV))
for (b, lab, col) in ((2, '복합 구매 유지', ORANGE), (1, '→ 구독 중심', GREEN), (0, '→ 저소비', BLUE)):
    est = main['A'][:, 2, b]
    ax1.fill_between(x, np.percentile(bA[:, :, 2, b], 2.5, axis=0), np.percentile(bA[:, :, 2, b], 97.5, axis=0), color=col, alpha=0.15, lw=0)
    ax1.plot(x, est, color=col, lw=2, marker='o', ms=5, label=lab)
ax1.axvspan(0.5, 2.5, color='#f3f6fa', zorder=0)
ax1.set_xticks(x); ax1.set_xticklabels(IV, fontsize=8.5); ax1.set_ylim(0, 1)
ax1.set_title('(가) 복합 구매 상태에서의 전이확률', fontsize=11, color=INK, loc='left', fontweight='bold')
ax1.legend(frameon=False, fontsize=9, loc='upper center', ncol=3)
style(ax1)
m = man[man.item == 'inapp_item']
ax2.fill_between(x, m.persist_lo, m.persist_hi, color=ORANGE, alpha=0.15, lw=0)
ax2.plot(x, m.persist, color=ORANGE, lw=2, marker='o', ms=5, label='구입자가 다음 해에도 구입')
ax2.fill_between(x, m.entry_lo, m.entry_hi, color=BLUE, alpha=0.15, lw=0)
ax2.plot(x, m.entry, color=BLUE, lw=2, marker='o', ms=5, label='비구입자가 다음 해에 구입')
for xi, v in zip(x, m.persist):
    ax2.annotate(f'{100 * v:.0f}%', (xi, v), textcoords='offset points', xytext=(0, 8), ha='center', fontsize=9, color=INK)
ax2.axvspan(0.5, 2.5, color='#f3f6fa', zorder=0)
ax2.set_xticks(x); ax2.set_xticklabels(IV, fontsize=8.5); ax2.set_ylim(0, 0.7)
ax2.set_title('(나) 앱 내 아이템 구입의 관측 전이율(모형 없음)', fontsize=11, color=INK, loc='left', fontweight='bold')
ax2.legend(frameon=False, fontsize=9, loc='upper center', ncol=1)
style(ax2)
fig.text(0.02, 0.012, '음영은 인앱결제 의무화와 가격 인상이 회상 기간에 들어가는 두 구간. 띠는 가구 군집 부트스트랩 95% 구간.', fontsize=8, color=MUTED, va='bottom')
fig.subplots_adjust(left=0.06, right=0.985, top=0.9, bottom=0.17, wspace=0.14)
fig.savefig(os.path.join(FIG, 'fig13_real_transitions.png'), dpi=170)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
np.set_printoptions(precision=3, suppress=True, linewidth=200)
print('seconds', summary['seconds'], 'boot valid', len(boots))
print(sel.round(1).to_string()); print(inv.round(1).to_string())
print(tr_df[tr_df.from_state == SL[2]].round(3).to_string())
print(occ_df.round(3).to_string()); print(con.round(3).to_string()); print(tests.round(4).to_string())
print(sens.round(3).T.to_string()); print(man.round(3).to_string())
print('summary and figures saved; covariate model next', round(time.time() - t_start), flush=True)

# ---------------------------------------------------------------------------
# G. 규제 강도 공변량 모형(기준 시점 2020년)
# ---------------------------------------------------------------------------
RATES = RX.sector_price_increase()
base = panel[panel.wave == 2020].set_index('id')
elig = base[base.android.notna() & base.use_music.notna() & base.use_webtoon.notna() & base.ott_use.notna()]
idx = np.array([i for i, pid in enumerate(IDS) if pid in elig.index])
b0 = elig.loc[IDS[idx]]
use = np.column_stack([(b0.ott_use == 1).astype(float), b0.use_music, b0.use_webtoon, b0.use_game.fillna(0)])
EX = RX.exposure_index(use, RATES)
EX_nv = RX.exposure_index(np.column_stack([np.zeros(len(b0)), b0.use_music, b0.use_webtoon, np.zeros(len(b0))]), RATES)   # 영상 제외 지수
age_z = (b0.age - b0.age.mean()) / b0.age.std()
COVN = ['가격 인상 노출 지수(z)', '안드로이드', '연령(z)']
# 영상 문항의 2024년 단절을 '2024년부터는 다른 문항'으로 표현한다(공변량 엔진은 문항별 묶음을 받지 않으므로).
Yc = np.full((len(idx), T, 5), np.nan)
Yc[:, :, [0, 1, 3]] = Y[idx][:, :, [0, 1, 3]]
b24 = WAVES.index(2024)
Yc[:, :b24, 2] = Y[idx][:, :b24, 2]
Yc[:, b24:, 4] = Y[idx][:, b24:, 2]
BG3 = [0, 1, 1, 2, 2]          # 이전 / 가격 인상기 / 이후


def cov_fit(Xc, b_groups, se=True, base_fit=None):
    return C.fit_cov(Yc, 3, X_init=Xc, X_trans=Xc, b_groups=b_groups, base=base_fit, se=se, tol=1e-7, maxit=COV_MAXIT)


cov_out = None
try:
    c_base = L.fit(Yc, 3, n_starts=NS, n_jobs=-2, maxit=2500, tol=1e-9)
    X_main = np.column_stack([EX['z'], b0.android.to_numpy(), age_z.to_numpy()])
    c1 = cov_fit(X_main, None, se=False, base_fit=c_base)
    c3 = cov_fit(X_main, BG3, base_fit=c_base)
    X_nv = np.column_stack([EX_nv['z'], b0.android.to_numpy(), age_z.to_numpy()])
    c3nv = cov_fit(X_nv, BG3, base_fit=c_base)
    crow = []
    for fitc, tag in ((c3, '주 지수(영상=OTT 이용)'), (c3nv, '영상 제외 지수')):
        for a in range(3):
            for b in range(3):
                if a == b:
                    continue
                for p, cn in enumerate(COVN):
                    i0, i1, i2 = (C.find_param(fitc, 'trans', a, b, p, g) for g in (0, 1, 2))
                    for cname, wts in (('이전(2020→21)', {i0: 1.0}), ('가격 인상기(2021→23)', {i1: 1.0}), ('이후(2023→25)', {i2: 1.0}),
                                       ('가격 인상기 − 이전', {i1: 1.0, i0: -1.0}), ('이후 − 이전', {i2: 1.0, i0: -1.0})):
                        crow.append(dict(index=tag, origin=SL[a], dest=SL[b], covariate=cn, quantity=cname, **C.wald_contrast(fitc, wts)))
    cov_coef = pd.DataFrame(crow)
    cov_coef.to_csv(os.path.join(OUT, 'real_cov_coefficients.csv'), index=False, encoding='utf-8-sig')
    cov_out = dict(n=int(len(idx)), n_excluded=int(N - len(idx)), exposure_mean=EX['mean'], exposure_sd=EX['sd'], android_share=float(b0.android.mean()),
                   rates=RATES, base=dict(loglik=c_base['loglik'], npar=int(c_base['npar']), bic=c_base['bic']),
                   common=dict(loglik=c1['loglik'], npar=int(c1['npar']), bic=c1['bic']),
                   regime=dict(loglik=c3['loglik'], npar=int(c3['npar']), bic=c3['bic'], info_pd=bool(c3['info_pd']), converged=bool(c3['converged'])),
                   lr_covariates=L.lr_test(c_base, c1), lr_interaction=L.lr_test(c1, c3), theta=c3['theta_jk'].round(4).tolist())
except Exception as e:                                   # 공변량 모형이 실패해도 앞의 결과는 저장한다
    cov_out = dict(error=repr(e))

summary['covariate_model'] = cov_out
summary['seconds'] = round(time.time() - t_start, 1)
with open(os.path.join(OUT, 'real_summary.json'), 'w', encoding='utf-8') as fh:
    json.dump(clean(summary), fh, ensure_ascii=False, indent=1)
print(json.dumps(cov_out, ensure_ascii=False)[:1500])
if cov_out and 'error' not in cov_out:
    q = cov_coef[(cov_coef.covariate == COVN[0]) & cov_coef.quantity.isin(['가격 인상기 − 이전', '이후 − 이전', '이전(2020→21)', '가격 인상기(2021→23)'])]
    print(q.round(3).to_string())
