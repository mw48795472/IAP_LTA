# -*- coding: utf-8 -*-
"""공변량 엔진 단위 검증:
(1) 개체별 전이행렬을 쓰는 forward-backward 우도 = 모든 잠재경로 전수 열거 우도
(2) 공변량이 없으면 기본 엔진(L.fit)과 같은 해
(3) 해석적 점수 = 로그우도의 수치 미분
(4) EM 로그우도 단조 증가
(5) 모의자료에서 심어 둔 계수의 복원(표준오차 대비)과 표준오차의 타당성"""
import itertools
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import lta_engine as L          # noqa: E402
import lta_covariates as C      # noqa: E402

rng = np.random.default_rng(11)

# (1) 전수 열거 -------------------------------------------------------------
N, T, J, K, P = 5, 4, 3, 3, 2
Y = (rng.random((N, T, J)) < 0.4).astype(float)
Y[rng.random(Y.shape) < 0.2] = np.nan
Y[1, 2, :] = np.nan
X = rng.normal(size=(N, P))
X0d = C.design_init(X, N)
Z, info = C.design_trans(X, N, T, b_groups=[0, 0, 1])
theta = rng.uniform(0.1, 0.9, (J, K))
Gam = np.zeros((X0d.shape[1], K)); Gam[:, 1:] = rng.normal(0, 0.7, (X0d.shape[1], K - 1))
W = np.zeros((K, Z.shape[2], K))
for a in range(K):
    W[a][:, [b for b in range(K) if b != a]] = rng.normal(0, 0.7, (Z.shape[2], K - 1))
P0, A = C.probabilities(theta, Gam, W, X0d, Z)
assert np.allclose(P0.sum(1), 1) and np.allclose(A.sum(3), 1)
M = (~np.isnan(Y)).astype(float); Y1 = np.nan_to_num(Y)
e = C.estep_cov(Y1 * M, (1 - Y1) * M, P0, A, theta)
brute = 0.0
for i in range(N):
    tot = 0.0
    for z in itertools.product(range(K), repeat=T):
        p = P0[i, z[0]]
        for t in range(1, T):
            p *= A[i, t - 1, z[t - 1], z[t]]
        for t in range(T):
            for j in range(J):
                if not np.isnan(Y[i, t, j]):
                    p *= theta[j, z[t]] if Y[i, t, j] == 1 else 1 - theta[j, z[t]]
        tot += p
    brute += np.log(tot)
assert abs(brute - e['loglik']) < 1e-10, (brute, e['loglik'])
assert np.allclose(e['gamma'].sum(2), 1) and np.allclose(e['xi'].sum((2, 3)), 1)

# (3) 점수 = 수치 미분 -------------------------------------------------------
v = C._pack(theta, Gam, W)
w1 = rng.uniform(0.5, 2.0, N)
ll, sc = C._loglik_score(v, Y1 * M, (1 - Y1) * M, M, X0d, Z, w1, K)
num = np.empty_like(v)
for i in range(len(v)):
    d = np.zeros(len(v)); d[i] = 1e-6
    num[i] = (C._loglik_score(v + d, Y1 * M, (1 - Y1) * M, M, X0d, Z, w1, K)[0]
              - C._loglik_score(v - d, Y1 * M, (1 - Y1) * M, M, X0d, Z, w1, K)[0]) / 2e-6
assert np.allclose(sc, num, atol=1e-6), np.abs(sc - num).max()
assert len(v) == C.n_parameters_cov(K, J, X0d.shape[1], info) == J * K + 2 * 3 + 6 * (3 + 2 * 2)

# (2) 공변량 없는 모형 = 기본 엔진 ---------------------------------------------
Ab = np.repeat(np.array([[0.85, 0.15], [0.25, 0.75]])[None], 3, axis=0)
Ab[2] = [[0.7, 0.3], [0.1, 0.9]]
Yb, _, _ = L.simulate_panel(1500, np.array([0.6, 0.4]), Ab, np.array([[0.1, 0.8], [0.2, 0.7], [0.15, 0.9]]), rng,
                            retention=np.array([0.9, 0.9, 0.9]))
for kw in (dict(), dict(homog=True), dict(a_groups=[0, 0, 1])):
    b = L.fit(Yb, 2, n_starts=4, tol=1e-13, maxit=20000, **kw)
    c = C.fit_cov(Yb, 2, base=b, tol=1e-13, se=False, **kw)
    assert abs(b['loglik'] - c['loglik']) < 1e-5 and c['npar'] == b['npar'], (kw, b['loglik'], c['loglik'])
    assert np.allclose(c['A'][0], b['A'], atol=1e-3) and np.allclose(c['theta_jk'], b['theta'][0], atol=1e-3)

# (4)(5) 복원 ---------------------------------------------------------------
N2, T2 = 6000, 5
theta2 = np.array([[0.03, 0.10, 0.45], [0.05, 0.20, 0.70], [0.10, 0.85, 0.90], [0.05, 0.40, 0.75]])
X2 = np.column_stack([rng.normal(size=N2), (rng.random(N2) < 0.7).astype(float)])
Gam2 = np.zeros((3, 3)); Gam2[0, 1:] = [-0.4, -1.3]; Gam2[1, 1:] = [0.6, 1.0]
bg = [0, 0, 1, 1]
Z2, info2 = C.design_trans(X2, N2, T2, homog=True, b_groups=bg)
W2 = np.zeros((3, Z2.shape[2], 3))
W2[0, 0, [1, 2]] = [-2.0, -3.5]; W2[1, 0, [0, 2]] = [-2.5, -2.3]; W2[2, 0, [0, 1]] = [-3.0, -1.8]
i_post_x0 = info2['G'] + 1 * info2['P'] + 0
W2[2, i_post_x0, 1] = 0.8                       # 뒤 국면: 공변량 1이 클수록 S3→S2
W2[1, i_post_x0, 0] = 0.5                       # 뒤 국면: 공변량 1이 클수록 S2→S1
Y2, S2, _ = C.simulate_panel_cov(theta2, Gam2, W2, X2, X2, T2, rng, homog=True, b_groups=bg,
                                 retention=np.array([0.95, 0.95, 0.95, 0.85]))
f = C.fit_cov(Y2, 3, X_init=X2, X_trans=X2, homog=True, b_groups=bg, n_base_starts=6, tol=1e-10)
assert f['converged'] and np.all(np.diff(f['trace']) > -1e-6), np.diff(f['trace']).min()
assert f['info_pd'], '정보행렬이 양의 정부호가 아닙니다.'
truth = C._pack(theta2, Gam2, W2)
zerr = (f['vec'] - truth) / f['se']
assert np.abs(zerr).max() < 4.5, (np.abs(zerr).max(), np.argmax(np.abs(zerr)))
assert np.abs(f['theta_jk'] - theta2).max() < 0.05
ia = C.find_param(f, 'trans', 2, 1, 0, 1)
ib = C.find_param(f, 'trans', 2, 1, 0, 0)
wc = C.wald_contrast(f, {ia: 1.0, ib: -1.0})
assert abs(wc['estimate'] - 0.8) < 3.5 * wc['se'] and wc['z'] > 2, wc
f0 = C.fit_cov(Y2, 3, X_init=X2, X_trans=X2, homog=True, n_base_starts=6, tol=1e-10, se=False)
lr = L.lr_test(f0, f)
assert lr['df'] == 12 and lr['p'] < 0.01, lr
print('PASS: 전수 열거 우도 일치, 무공변량=기본 엔진, 점수=수치 미분, EM 단조, 계수 복원(최대 |z| = %.2f), 상호작용 Wald z = %.2f, LR p = %.2g'
      % (np.abs(zerr).max(), wc['z'], lr['p']))
