# -*- coding: utf-8 -*-
"""엔진 단위 검증: (1) forward-backward 우도 = 모든 잠재경로 전수 열거 우도,
(2) 사후확률 합 = 1, (3) K=1 의 응답확률 = 관측 문항 평균, (4) EM 로그우도 단조 증가,
(5) 가중치 적합 = 자료 복제 적합."""
import itertools, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import lta_engine as L

rng = np.random.default_rng(7)
N, T, J, K = 6, 4, 3, 3
Y = (rng.random((N, T, J)) < 0.4).astype(float)
Y[rng.random(Y.shape) < 0.2] = np.nan
Y[2, 1, :] = np.nan                      # 조사 미참여 시점
pi, A, theta = L.random_init(K, T, J, rng)
theta = rng.uniform(0.1, 0.9, (T, J, K))  # 시점별 자유 응답확률
M = (~np.isnan(Y)).astype(float); Y1 = np.nan_to_num(Y)
e = L.estep(Y1 * M, (1 - Y1) * M, pi, A, theta)
brute = 0.0
for i in range(N):
    tot = 0.0
    for z in itertools.product(range(K), repeat=T):
        p = pi[z[0]]
        for t in range(1, T):
            p *= A[t - 1, z[t - 1], z[t]]
        for t in range(T):
            for j in range(J):
                if not np.isnan(Y[i, t, j]):
                    p *= theta[t, j, z[t]] if Y[i, t, j] == 1 else 1 - theta[t, j, z[t]]
        tot += p
    brute += np.log(tot)
assert abs(brute - e['loglik']) < 1e-10, (brute, e['loglik'])
assert np.allclose(e['gamma'].sum(2), 1)
assert np.allclose(e['xi_sum'].sum((1, 2)), N)

Yb = (rng.random((300, 4, 3)) < 0.3).astype(float); Yb[rng.random(Yb.shape) < 0.1] = np.nan
f1 = L.fit(Yb, 1, n_starts=1)
assert np.allclose(f1['theta'][0, :, 0], np.nanmean(Yb, axis=(0, 1)), atol=1e-6)
f2 = L.fit(Yb, 2, n_starts=3)
assert np.all(np.diff(f2['trace']) > -1e-7)
w = rng.integers(0, 3, 300).astype(float)
fw = L.fit(Yb, 2, n_starts=1, init=(f2['pi'], f2['A'], f2['theta']), w=w)
fr = L.fit(np.repeat(Yb, w.astype(int), axis=0), 2, n_starts=1, init=(f2['pi'], f2['A'], f2['theta']))
assert abs(fw['loglik'] - fr['loglik']) < 1e-6 and np.allclose(fw['A'], fr['A'], atol=1e-6)
assert L.n_parameters(3, 5, 4) == 2 + 4 * 6 + 12 and L.n_parameters(3, 5, 4, homog=True) == 2 + 6 + 12
fh = L.fit(Yb, 2, n_starts=3, homog=True); fg = L.fit(Yb, 2, n_starts=3, a_groups=[0, 0, 1])
assert np.allclose(fh['A'][0], fh['A'][2]) and np.allclose(fg['A'][0], fg['A'][1]) and not np.allclose(fg['A'][1], fg['A'][2])
assert fh['loglik'] <= fg['loglik'] + 1e-6 <= f2['loglik'] + 2e-6 and fg['npar'] == 1 + 2 * 2 + 6
print('PASS: 전수 열거 우도 일치, 사후확률 정규화, K=1=문항 평균, EM 단조, 가중=복제 적합')
