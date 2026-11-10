# -*- coding: utf-8 -*-
"""
lta_covariates.py — 공변량이 있는 잠재전이분석(초기 상태와 전이확률의 다항 로짓)

기본 엔진(lta_engine.py)은 그대로 두고, 그 위에 공변량 모형을 얹는다.

모형
  초기 상태   P(Z_i1 = k | x0_i)              = softmax_k( g0_k + x0_i' g_k ),           기준 범주: 상태 1 (g = 0)
  전이        P(Z_i,t+1 = b | Z_it = a, x_it) = softmax_b( a_{G(t),a,b} + x_it' b_{H(t),a,b} ), 기준 범주: 머무름(b = a)
  측정        P(Y_itj = 1 | Z_it = k) = theta_jk   (시점 간 동일)

  G(t) : 절편 묶음(a_groups). 기본값은 구간마다 자유 → 모든 사람에게 공통인 시기 효과를 통제한다.
  H(t) : 계수 묶음(b_groups). 예: [0,0,1,1] 이면 앞 국면과 뒤 국면의 공변량 계수가 따로 추정되고,
         두 계수의 차이가 '국면 × 공변량' 상호작용(규제 이후 노출이 큰 사람의 전이가 더 달라졌는가)이다.
  b_{.,a,b} 는 '상태 a 에 머무름' 대비 'a → b 이동'의 로그 오즈에 대한 공변량 1단위의 효과다.

추정
  E-step  개체별 전이행렬을 쓰는 scaled forward-backward(결측 응답은 주변화).
  M-step  응답확률은 닫힌 해, 초기·전이 로짓은 기대빈도를 가중치로 하는 뉴턴법(일반화 EM).
  시작값  공변량 없는 모형(L.fit)의 해에서 출발한다(상태 라벨이 유지된다).
  표준오차 관측 우도의 점수(score)를 해석적으로 구하고 그 중심차분으로 관측 정보행렬을 만든다.

공변량은 결측이 없어야 하며, 연속형은 표준화해서 넣는 것을 권한다.
"""
import numpy as np

import lta_engine as L

CLIP = L.CLIP


def _softmax(eta):
    eta = eta - eta.max(-1, keepdims=True)
    p = np.exp(eta)
    return p / p.sum(-1, keepdims=True)


def _relabel(g):
    return np.unique(np.asarray(g, dtype=int), return_inverse=True)[1].ravel()


# ---------------------------------------------------------------------------
# 1. 설계행렬
# ---------------------------------------------------------------------------
def design_init(X_init, N):
    """(N, 1+P0): 절편 + 초기 상태 공변량."""
    one = np.ones((N, 1))
    if X_init is None:
        return one
    X = np.asarray(X_init, dtype=float).reshape(N, -1)
    assert not np.isnan(X).any(), '초기 상태 공변량에 결측이 있습니다.'
    return np.hstack([one, X])


def design_trans(X_trans, N, T, a_groups=None, b_groups=None, homog=False):
    """(N, T-1, G + H·P): 절편 묶음 가변수 + (계수 묶음 × 공변량).

    X_trans 는 None, (N, P)(시점 불변), (N, T-1, P)(구간별; t 번째 구간에는 출발 시점의 값) 중 하나.
    """
    ag = _relabel(L._groups(T, homog, a_groups))
    G = int(ag.max()) + 1
    if X_trans is None:
        P, H, bg = 0, 1, np.zeros(T - 1, dtype=int)
        X = np.zeros((N, T - 1, 0))
    else:
        X = np.asarray(X_trans, dtype=float)
        if X.ndim == 2:
            X = np.repeat(X[:, None, :], T - 1, axis=1)
        assert X.shape[:2] == (N, T - 1) and not np.isnan(X).any(), '전이 공변량의 모양 또는 결측을 확인하세요.'
        P = X.shape[2]
        bg = np.zeros(T - 1, dtype=int) if b_groups is None else _relabel(b_groups)
        assert len(bg) == T - 1
        H = int(bg.max()) + 1
    Z = np.zeros((N, T - 1, G + H * P))
    for t in range(T - 1):
        Z[:, t, ag[t]] = 1.0
        if P:
            Z[:, t, G + bg[t] * P:G + (bg[t] + 1) * P] = X[:, t]
    return Z, dict(G=G, H=H, P=P, a_groups=ag, b_groups=bg)


def probabilities(theta_jk, Gam, W, X0d, Z):
    """모수 → 초기확률 P0 (N,K), 전이확률 A (N,T-1,K,K)."""
    P0 = _softmax(X0d @ Gam)
    A = _softmax(np.einsum('ntd,adb->ntab', Z, W))
    return P0, A


# ---------------------------------------------------------------------------
# 2. E-step
# ---------------------------------------------------------------------------
def estep_cov(YM, NM, P0, A, theta_jk, w=None):
    """gamma (N,T,K), xi (N,T-1,K,K), 로그우도. A 는 개체별 전이확률."""
    N, T, _ = YM.shape
    K = P0.shape[1]
    w = np.ones(N) if w is None else w
    B = L._emission(YM, NM, np.repeat(theta_jk[None], T, axis=0))
    alpha = np.empty((N, T, K))
    c = np.empty((N, T))
    a = B[:, 0] * P0
    c[:, 0] = a.sum(1)
    alpha[:, 0] = a / c[:, [0]]
    for t in range(1, T):
        a = np.einsum('na,nab->nb', alpha[:, t - 1], A[:, t - 1]) * B[:, t]
        c[:, t] = a.sum(1)
        alpha[:, t] = a / c[:, [t]]
    beta = np.ones((N, T, K))
    xi = np.empty((N, T - 1, K, K))
    for t in range(T - 2, -1, -1):
        right = B[:, t + 1] * beta[:, t + 1] / c[:, [t + 1]]
        beta[:, t] = np.einsum('nab,nb->na', A[:, t], right)
        xi[:, t] = alpha[:, t][:, :, None] * A[:, t] * right[:, None, :]
    gamma = alpha * beta
    gamma /= gamma.sum(2, keepdims=True)
    ind = np.log(c).sum(1)
    return dict(gamma=gamma, xi=xi, loglik=float((w * ind).sum()), ind_loglik=ind)


# ---------------------------------------------------------------------------
# 3. M-step: 기대빈도를 가중치로 하는 다항 로짓(뉴턴법, 보폭 반감)
# ---------------------------------------------------------------------------
def _mlogit_q(Zd, R, nrow, Wc):
    eta = Zd @ Wc
    m = eta.max(1, keepdims=True)
    lse = (m + np.log(np.exp(eta - m).sum(1, keepdims=True))).ravel()
    return float((R * eta).sum() - (nrow * lse).sum())


def _mlogit_newton(Zd, R, Wc, ref, n_iter=2, ridge=1e-8):
    """Zd (M,D) 설계, R (M,K) 기대빈도, Wc (D,K) 계수(기준 범주 ref 의 열은 0으로 고정)."""
    D, K = Wc.shape
    free = [b for b in range(K) if b != ref]
    nrow = R.sum(1)
    q_old = _mlogit_q(Zd, R, nrow, Wc)
    for _ in range(n_iter):
        p = _softmax(Zd @ Wc)
        grad = (Zd.T @ (R - nrow[:, None] * p))[:, free].ravel(order='F')
        Hn = np.empty((len(free) * D, len(free) * D))          # -헤시안(양의 정부호)
        for i, b in enumerate(free):
            for j, cc in enumerate(free):
                wgt = nrow * p[:, b] * ((1.0 if b == cc else 0.0) - p[:, cc])
                Hn[i * D:(i + 1) * D, j * D:(j + 1) * D] = Zd.T @ (Zd * wgt[:, None])
        try:
            step = np.linalg.solve(Hn + ridge * np.eye(len(grad)), grad)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(Hn + 1e-6 * np.eye(len(grad)), grad, rcond=None)[0]
        s, ok = 1.0, False
        for _h in range(20):
            Wn = Wc.copy()
            Wn[:, free] += s * step.reshape(D, len(free), order='F')
            q_new = _mlogit_q(Zd, R, nrow, Wn)
            if q_new >= q_old - 1e-10:
                ok = True
                break
            s *= 0.5
        if not ok:
            break
        done = abs(q_new - q_old) < 1e-10 * (1 + abs(q_old))
        Wc, q_old = Wn, q_new
        if done:
            break
    return Wc


# ---------------------------------------------------------------------------
# 4. 모수 벡터 ↔ 배열, 로그우도와 점수
# ---------------------------------------------------------------------------
def _pack(theta_jk, Gam, W):
    K = Gam.shape[1]
    parts = [np.log(theta_jk / (1 - theta_jk)).ravel(), Gam[:, 1:].ravel()]
    for a in range(K):
        parts.append(W[a][:, [b for b in range(K) if b != a]].ravel())
    return np.concatenate(parts)


def _unpack(v, J, K, D0, D):
    i = J * K
    theta_jk = 1.0 / (1.0 + np.exp(-v[:i].reshape(J, K)))
    Gam = np.zeros((D0, K))
    Gam[:, 1:] = v[i:i + D0 * (K - 1)].reshape(D0, K - 1)
    i += D0 * (K - 1)
    W = np.zeros((K, D, K))
    for a in range(K):
        free = [b for b in range(K) if b != a]
        W[a][:, free] = v[i:i + D * (K - 1)].reshape(D, K - 1)
        i += D * (K - 1)
    return theta_jk, Gam, W


def _loglik_score(v, YM, NM, M, X0d, Z, w, K):
    """모수 벡터 v 에서의 로그우도와 점수(피셔 항등식: 관측 우도의 기울기 = 완전자료 점수의 사후 기댓값)."""
    N, T, J = YM.shape
    D0, D = X0d.shape[1], Z.shape[2]
    theta_jk, Gam, W = _unpack(v, J, K, D0, D)
    theta_jk = np.clip(theta_jk, CLIP, 1 - CLIP)
    P0, A = probabilities(theta_jk, Gam, W, X0d, Z)
    e = estep_cov(YM, NM, P0, A, theta_jk, w)
    g = e['gamma'] * w[:, None, None]
    g2 = g.reshape(-1, K)
    s_theta = YM.reshape(-1, J).T @ g2 - (M.reshape(-1, J).T @ g2) * theta_jk
    s_init = (X0d.T @ (w[:, None] * (e['gamma'][:, 0] - P0)))[:, 1:]
    parts = [s_theta.ravel(), s_init.ravel()]
    Zf = Z.reshape(-1, D)
    for a in range(K):
        r = (w[:, None, None] * (e['xi'][:, :, a, :] - e['gamma'][:, :-1, a][:, :, None] * A[:, :, a, :])).reshape(-1, K)
        parts.append((Zf.T @ r)[:, [b for b in range(K) if b != a]].ravel())
    return e['loglik'], np.concatenate(parts)


def n_parameters_cov(K, J, D0, info):
    return J * K + (K - 1) * D0 + K * (K - 1) * (info['G'] + info['H'] * info['P'])


# ---------------------------------------------------------------------------
# 5. 적합
# ---------------------------------------------------------------------------
def _start_from_base(base, K, D0, D, info):
    """공변량 없는 해 → 로짓 모수의 시작값(공변량 계수는 0)."""
    theta_jk = np.clip(np.asarray(base['theta'])[0], 1e-4, 1 - 1e-4)
    pi = np.clip(np.asarray(base['pi']), 1e-6, None)
    Gam = np.zeros((D0, K))
    Gam[0] = np.log(pi / pi[0])
    W = np.zeros((K, D, K))
    A = np.clip(np.asarray(base['A']), 1e-6, None)
    for g in range(info['G']):
        Ag = A[info['a_groups'] == g].mean(0)
        for a in range(K):
            W[a, g, :] = np.log(Ag[a] / Ag[a, a])
    return theta_jk, Gam, W


def fit_cov(Y, K, X_init=None, X_trans=None, a_groups=None, b_groups=None, homog=False, base=None,
            n_starts=1, maxit=3000, tol=1e-9, seed=1104, w=None, n_base_starts=10, se=True, init=None):
    """공변량 잠재전이모형의 최대우도 추정.

    base  : 같은 절편 묶음으로 적합한 공변량 없는 모형(L.fit 결과). 없으면 여기서 적합한다.
    init  : (theta_jk, Gam, W) 를 직접 주면 그 값에서 출발한다(몬테카를로의 warm start).
    n_starts > 1 이면 공변량 계수에 잡음을 더한 시작값을 추가로 시도해 로그우도가 가장 큰 해를 고른다.
    """
    Y = np.asarray(Y, dtype=float)
    N, T, J = Y.shape
    M = (~np.isnan(Y)).astype(float)
    YM = np.nan_to_num(Y, nan=0.0) * M
    NM = M - YM
    YM2, M2 = YM.reshape(-1, J), M.reshape(-1, J)
    w = np.ones(N) if w is None else np.asarray(w, dtype=float)
    X0d = design_init(X_init, N)
    Z, info = design_trans(X_trans, N, T, a_groups, b_groups, homog)
    D0, D = X0d.shape[1], Z.shape[2]
    Zf = Z.reshape(-1, D)
    if init is None:
        if base is None:
            base = L.fit(Y, K, n_starts=n_base_starts, a_groups=a_groups, homog=homog, seed=seed, w=w)
        start0 = _start_from_base(base, K, D0, D, info)
    else:
        start0 = tuple(np.array(x, dtype=float) for x in init)
    rng = np.random.default_rng(seed)

    def run(theta_jk, Gam, W):
        trace, converged = [], False
        for it in range(1, maxit + 1):
            P0, A = probabilities(theta_jk, Gam, W, X0d, Z)
            e = estep_cov(YM, NM, P0, A, theta_jk, w)
            trace.append(e['loglik'])
            if it > 1 and abs(trace[-1] - trace[-2]) < tol * (1.0 + abs(trace[-1])):
                converged = True
                break
            if it == maxit:
                break
            g = e['gamma'] * w[:, None, None]
            g2 = g.reshape(-1, K)
            den = M2.T @ g2
            theta_jk = np.clip(np.where(den > 0, (YM2.T @ g2) / np.maximum(den, 1e-300), theta_jk), CLIP, 1 - CLIP)
            Gam = _mlogit_newton(X0d, g[:, 0, :], Gam, ref=0)
            W = W.copy()
            for a in range(K):
                R = (e['xi'][:, :, a, :] * w[:, None, None]).reshape(-1, K)
                W[a] = _mlogit_newton(Zf, R, W[a], ref=a)
        return dict(theta_jk=theta_jk, Gam=Gam, W=W, loglik=e['loglik'], trace=np.array(trace), iterations=it,
                    converged=converged, gamma=e['gamma'], P0=P0, A=A)

    best = run(*start0)
    for _s in range(1, n_starts):
        th, Gm, Wm = (x.copy() for x in start0)
        Gm[1:, 1:] += rng.normal(0, 0.3, Gm[1:, 1:].shape)
        for a in range(K):
            free = [b for b in range(K) if b != a]
            Wm[a][info['G']:, free] += rng.normal(0, 0.3, (D - info['G'], K - 1))
        cand = run(th, Gm, Wm)
        if cand['loglik'] > best['loglik']:
            best = cand
    npar = n_parameters_cov(K, J, D0, info)
    wsum = float(w.sum())
    out = dict(K=K, J=J, T=T, info=info, D0=D0, D=D, npar=npar, n=wsum, aic=-2 * best['loglik'] + 2 * npar,
               bic=-2 * best['loglik'] + np.log(wsum) * npar, theta=np.repeat(best['theta_jk'][None], T, axis=0), **best)
    if se:
        out.update(standard_errors(out, YM, NM, M, X0d, Z, w))
    return out


def standard_errors(fit, YM, NM, M, X0d, Z, w, h=1e-5):
    """관측 정보행렬(점수의 중심차분) → 공분산행렬과 표준오차. 모수 순서는 _pack 과 같다."""
    K, J = fit['K'], fit['J']
    v = _pack(np.clip(fit['theta_jk'], 1e-7, 1 - 1e-7), fit['Gam'], fit['W'])
    n = len(v)
    H = np.empty((n, n))
    for i in range(n):
        d = np.zeros(n)
        d[i] = h
        H[:, i] = (_loglik_score(v + d, YM, NM, M, X0d, Z, w, K)[1] - _loglik_score(v - d, YM, NM, M, X0d, Z, w, K)[1]) / (2 * h)
    H = 0.5 * (H + H.T)
    info_mat = -H
    try:
        cov = np.linalg.inv(info_mat)
        pd_ok = bool(np.all(np.linalg.eigvalsh(info_mat) > 0))
    except np.linalg.LinAlgError:
        cov, pd_ok = np.linalg.pinv(info_mat), False
    return dict(vec=v, cov=cov, se=np.sqrt(np.clip(np.diag(cov), 0, None)), info_pd=pd_ok)


# ---------------------------------------------------------------------------
# 6. 결과 정리
# ---------------------------------------------------------------------------
def param_index(fit):
    """모수 벡터의 각 원소에 대한 설명(part, origin, dest, term)."""
    K, J, D0, info = fit['K'], fit['J'], fit['D0'], fit['info']
    G, H, P = info['G'], info['H'], info['P']
    rows = [dict(part='theta', origin=None, dest=k, term=f'item{j}', group=None) for j in range(J) for k in range(K)]
    rows += [dict(part='init', origin=None, dest=k, term='const' if d == 0 else f'x{d - 1}', group=None)
             for d in range(D0) for k in range(1, K)]
    for a in range(K):
        for d in range(G + H * P):
            for b in [b for b in range(K) if b != a]:
                if d < G:
                    rows.append(dict(part='trans', origin=a, dest=b, term='const', group=d))
                else:
                    rows.append(dict(part='trans', origin=a, dest=b, term=f'x{(d - G) % P}', group=(d - G) // P))
    return rows


def coef_table(fit, init_names=None, trans_names=None, state_labels=None):
    """추정값, 표준오차, z, p 를 담은 표(pandas DataFrame). theta 는 로짓 척도다."""
    import pandas as pd
    from scipy.stats import norm
    rows = param_index(fit)
    sl = state_labels or [f'S{k + 1}' for k in range(fit['K'])]
    out = []
    for r, est, se in zip(rows, fit['vec'], fit.get('se', np.full(len(rows), np.nan))):
        term = r['term']
        if term.startswith('x'):
            names = init_names if r['part'] == 'init' else trans_names
            term = names[int(term[1:])] if names else term
        z = est / se if se and se > 0 else np.nan
        out.append(dict(part=r['part'], origin=None if r['origin'] is None else sl[r['origin']], dest=sl[r['dest']],
                        term=term, coef_group=r['group'], estimate=est, se=se, z=z, p=float(2 * norm.sf(abs(z))) if z == z else np.nan))
    return pd.DataFrame(out)


def find_param(fit, part, origin, dest, term_index, group):
    """param_index 에서 조건에 맞는 원소의 위치."""
    for i, r in enumerate(param_index(fit)):
        if r['part'] == part and r['origin'] == origin and r['dest'] == dest and r['term'] == f'x{term_index}' and r['group'] == group:
            return i
    raise KeyError((part, origin, dest, term_index, group))


def wald_contrast(fit, weights):
    """선형 대비 c'v 의 추정값, 표준오차, z, p. weights = {모수 위치: 계수}."""
    from scipy.stats import norm
    c = np.zeros(len(fit['vec']))
    for i, val in weights.items():
        c[i] = val
    est = float(c @ fit['vec'])
    se = float(np.sqrt(max(c @ fit['cov'] @ c, 0)))
    z = est / se if se > 0 else np.nan
    return dict(estimate=est, se=se, z=z, p=float(2 * norm.sf(abs(z))) if z == z else np.nan)


def predict_transition(fit, x, coef_group, intercept_group):
    """공변량 값 x(길이 P)에서의 전이행렬 (K,K)."""
    info = fit['info']
    z = np.zeros(fit['D'])
    z[intercept_group] = 1.0
    if info['P']:
        z[info['G'] + coef_group * info['P']:info['G'] + (coef_group + 1) * info['P']] = np.asarray(x, dtype=float)
    return _softmax(np.einsum('d,adb->ab', z, fit['W']))


# ---------------------------------------------------------------------------
# 7. 공변량이 있는 모의패널
# ---------------------------------------------------------------------------
def simulate_panel_cov(theta_jk, Gam, W, X_init, X_trans, T, rng, a_groups=None, b_groups=None, homog=False,
                       retention=None, reentry=0.30, item_missing=0.01, buyer_items=(0, 1),
                       buyer_penalty=0.05, nonbuyer_bonus=0.01):
    """초기·전이 로짓 모형에서 잠재경로와 응답을 만들고, 기본 엔진과 같은 방식으로 이탈과 문항 무응답을 덧씌운다."""
    N = np.asarray(X_trans if X_trans is not None else X_init).shape[0]
    J, K = theta_jk.shape
    X0d = design_init(X_init, N)
    Z, _ = design_trans(X_trans, N, T, a_groups, b_groups, homog)
    P0, A = probabilities(theta_jk, Gam, W, X0d, Z)
    S = np.empty((N, T), dtype=int)
    S[:, 0] = (rng.random(N)[:, None] > P0.cumsum(1)).sum(1).clip(0, K - 1)
    for t in range(1, T):
        cum = A[np.arange(N), t - 1, S[:, t - 1]].cumsum(1)
        S[:, t] = (rng.random(N)[:, None] > cum).sum(1).clip(0, K - 1)
    Pr = np.stack([theta_jk[:, S[:, t]].T for t in range(T)], axis=1)
    Yfull = (rng.random((N, T, J)) < Pr).astype(float)
    Y = Yfull.copy()
    resp = np.ones((N, T), dtype=bool)
    if retention is not None:
        for t in range(1, T):
            prev = resp[:, t - 1]
            buyer = np.zeros(N, dtype=bool)
            for j in buyer_items:
                buyer |= (Yfull[:, t - 1, j] == 1) & prev
            p = np.where(prev, np.where(buyer, retention[t - 1] - buyer_penalty, retention[t - 1] + nonbuyer_bonus), reentry)
            resp[:, t] = rng.random(N) < np.clip(p, 0, 1)
    Y[~resp] = np.nan
    if item_missing > 0:
        Y[rng.random(Y.shape) < item_missing] = np.nan
    return Y, S, resp
