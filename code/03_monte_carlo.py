# -*- coding: utf-8 -*-
"""
03_monte_carlo.py — 설계 타당성 몬테카를로 실험

실험 A (조건 12개 × 200회): 표본 크기 N 과 심어 둔 변화 Δ 에 따라
  (1) 전이확률이 변하지 않았을 때(Δ=0) 전이 동질성 우도비 검정의 기각률이 명목 5%에 가까운가(크기),
  (2) 2022→2023 이후 S3→S2 전이확률이 Δ 만큼 높아졌을 때 이를 검출할 확률(검정력),
  (3) 변화 크기 추정값의 편의와 RMSE, 전이·응답확률의 평균절대오차.
실험 B (N 3개 × 100회, Δ=0.06): BIC 가 참 상태 수(K=3)를 고르는 비율(K=2,3,4 비교).

실행
  python 03_monte_carlo.py                     # 전체. 코어 수에 따라 10~30분
  python 03_monte_carlo.py --reps 20 --reps-k 10   # 빠른 점검
결과: ../outputs/mc_replicates.csv, mc_summary.csv, mc_kselect_replicates.csv, mc_kselect_summary.csv
노트북은 이 CSV 가 있으면 다시 돌리지 않고 읽어 온다.
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lta_engine as L          # noqa: E402
import study_design as D        # noqa: E402

N_GRID = [500, 2000, 8000]
DELTA_GRID = [0.0, 0.03, 0.06, 0.10]
MC_SEED = 20261107
REGIMES = [0, 0, 1, 1]


def _simulate(N, delta, rep, stream):
    rng = np.random.default_rng([MC_SEED, stream, N, int(round(delta * 1000)), rep])
    A_true = D.transition_matrices(delta)
    Y, _, _ = L.simulate_panel(N, D.PI0, A_true, D.THETA, rng, retention=D.RETENTION,
                               reentry=D.REENTRY, item_missing=D.ITEM_MISSING)
    return Y, A_true, int(rng.integers(1, 2**31 - 1))


def one_replicate(N, delta, rep):
    """실험 A: 모의패널 1개 → K=3 이질/동질 전이 모형 적합, 우도비 검정, 변화 크기 추정."""
    Y, A_true, seed = _simulate(N, delta, rep, 1)
    truth = (D.PI0, A_true, D.theta_by_wave())
    # 참값 warm start 1개 + 무작위 초기값 1개. 실제 분석에서는 참값을 모르므로 본 분석(노트북)은
    # 무작위 초기값만 쓴다. 여기서는 계산량을 줄이기 위한 관행적 처리다.
    het = L.fit(Y, 3, n_starts=2, init=truth, seed=seed, maxit=1500, tol=1e-8)
    hom = L.fit(Y, 3, n_starts=2, homog=True, init=truth, seed=seed, maxit=1500, tol=1e-8)
    # 두 국면 모형: 2020→21, 21→22 가 한 전이행렬, 22→23, 23→24 가 다른 전이행렬을 공유
    reg = L.fit(Y, 3, n_starts=2, a_groups=REGIMES, init=truth, seed=seed, maxit=1500, tol=1e-8)
    lr = L.lr_test(hom, het)          # 총괄 검정: 동질 vs 구간별 자유 (df=18)
    lr2 = L.lr_test(hom, reg)         # 초점 검정: 동질 vs 두 국면 (df=6)
    pre = het['A'][[0, 1], 2, 1].mean()
    post = het['A'][list(D.SHIFT_INTERVALS), 2, 1].mean()
    return dict(N=N, delta=delta, rep=rep, lr_stat=lr['stat'], lr_df=lr['df'], lr_p=lr['p'],
                lr2_stat=lr2['stat'], lr2_df=lr2['df'], lr2_p=lr2['p'],
                shift_hat=float(post - pre), shift_hat_regime=float(reg['A'][2, 2, 1] - reg['A'][0, 2, 1]),
                mae_A=float(np.abs(het['A'] - A_true).mean()),
                mae_theta=float(np.abs(het['theta'][0] - D.THETA).mean()),
                max_err_theta=float(np.abs(het['theta'][0] - D.THETA).max()),
                converged=bool(het['converged'] and hom['converged']))


def one_kselect(N, rep, delta=D.DELTA_MAIN):
    """실험 B: 모의패널 1개 → K=2,3,4 의 BIC 비교."""
    Y, A_true, seed = _simulate(N, delta, rep, 2)
    truth = (D.PI0, A_true, D.theta_by_wave())
    k3 = L.fit(Y, 3, n_starts=2, init=truth, seed=seed, maxit=1500, tol=1e-8)
    k2 = L.fit(Y, 2, n_starts=3, seed=seed, maxit=600, tol=1e-7)
    k4 = L.fit(Y, 4, n_starts=3, seed=seed, maxit=400, tol=1e-6)
    bics = {2: k2['bic'], 3: k3['bic'], 4: k4['bic']}
    return dict(N=N, delta=delta, rep=rep, k_bic=min(bics, key=bics.get),
                bic2=k2['bic'], bic3=k3['bic'], bic4=k4['bic'])


def summarise(df):
    rows = []
    for (n, d), g in df.groupby(['N', 'delta']):
        r = len(g)
        rej = (g['lr_p'] < 0.05).mean()
        rej2 = (g['lr2_p'] < 0.05).mean()
        rows.append(dict(N=n, delta=d, reps=r,
                         reject_rate=rej, reject_mcse=np.sqrt(rej * (1 - rej) / r),
                         reject_rate_regime=rej2, reject_mcse_regime=np.sqrt(rej2 * (1 - rej2) / r),
                         shift_regime_mean=g['shift_hat_regime'].mean(),
                         shift_regime_rmse=np.sqrt(((g['shift_hat_regime'] - d) ** 2).mean()),
                         shift_mean=g['shift_hat'].mean(), shift_bias=g['shift_hat'].mean() - d,
                         shift_sd=g['shift_hat'].std(ddof=1),
                         shift_rmse=np.sqrt(((g['shift_hat'] - d) ** 2).mean()),
                         mae_A=g['mae_A'].mean(), mae_theta=g['mae_theta'].mean(),
                         pct_converged=100 * g['converged'].mean()))
    return pd.DataFrame(rows)


def summarise_k(dk):
    rows = []
    for n, g in dk.groupby('N'):
        rows.append(dict(N=n, reps=len(g), pct_bic_k2=100 * (g['k_bic'] == 2).mean(),
                         pct_bic_k3=100 * (g['k_bic'] == 3).mean(),
                         pct_bic_k4=100 * (g['k_bic'] == 4).mean(),
                         mean_dbic_3_vs_2=(g['bic2'] - g['bic3']).mean(),
                         mean_dbic_3_vs_4=(g['bic4'] - g['bic3']).mean()))
    return pd.DataFrame(rows)


def run(reps=200, reps_k=100, n_jobs=-2, out_dir=None, verbose=True):
    from joblib import Parallel, delayed
    out_dir = out_dir or os.path.join(HERE, '..', 'outputs')
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    tasks = [(n, d, r) for n in N_GRID for d in DELTA_GRID for r in range(reps)]
    res = Parallel(n_jobs=n_jobs, verbose=5 if verbose else 0)(
        delayed(one_replicate)(*t) for t in tasks)
    df = pd.DataFrame(res)
    df.to_csv(os.path.join(out_dir, 'mc_replicates.csv'), index=False)
    sm = summarise(df)
    sm.to_csv(os.path.join(out_dir, 'mc_summary.csv'), index=False)
    if verbose:
        print(f'A done: {len(df)} replicates in {time.time() - t0:.0f}s')
        print(sm.round(4).to_string(index=False))
    tk = [(n, r) for n in N_GRID for r in range(reps_k)]
    resk = Parallel(n_jobs=n_jobs, verbose=5 if verbose else 0)(
        delayed(one_kselect)(*t) for t in tk)
    dk = pd.DataFrame(resk)
    dk.to_csv(os.path.join(out_dir, 'mc_kselect_replicates.csv'), index=False)
    sk = summarise_k(dk)
    sk.to_csv(os.path.join(out_dir, 'mc_kselect_summary.csv'), index=False)
    if verbose:
        print(f'B done: {len(dk)} replicates, total {time.time() - t0:.0f}s')
        print(sk.round(2).to_string(index=False))
    return df, sm, dk, sk


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--reps', type=int, default=200)
    ap.add_argument('--reps-k', type=int, default=100)
    ap.add_argument('--jobs', type=int, default=-2)
    a = ap.parse_args()
    run(a.reps, a.reps_k, a.jobs)
