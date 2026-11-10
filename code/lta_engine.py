# -*- coding: utf-8 -*-
"""
lta_engine.py — 이진 지표 잠재전이분석(LTA; 잠재 마코프 모형) 엔진 (numpy 구현)

모형
  Z_it ∈ {1..K}      : 개체 i, 시점 t 의 잠재상태 (1차 마코프)
  Y_itj ∈ {0,1,NA}   : 문항 j 의 이진 응답 (상태 내 조건부 독립)
  pi[k]              : 첫 시점 상태확률
  A[t,a,b]           : t→t+1 구간 전이확률 P(Z_{t+1}=b | Z_t=a)
  theta[t,j,k]       : P(Y_tj = 1 | Z_t = k)  (측정불변이면 t 에 대해 동일)

추정
  결측 응답은 0으로 바꾸지 않고 우도에서 주변화한다(MAR 가정의 FIML).
  scaled forward-backward 로 E-step, 닫힌 해로 M-step 을 수행하는 EM.
  개체 가중치 w 를 지원하므로, 부트스트랩은 다항 재표집 가중치로 처리한다.

이 파일은 노트북(01_...ipynb)과 몬테카를로(03_monte_carlo.py)가 함께 불러 쓴다.
R 구현(02_RUN_ALL.R)과 같은 우도·같은 모수 수 정의를 사용한다.
"""
import numpy as np

CLIP = 1e-8  # 응답확률이 정확히 0/1이 되어 log(0)이 생기는 것을 막는 경계값


# ---------------------------------------------------------------------------
# 1. 자료 구조 변환
# ---------------------------------------------------------------------------
def panel_to_array(df, id_col, wave_col, items, waves):
    """long 형식(개체×시점 한 행) 자료를 (N, T, J) 배열로 바꾼다.

    관측되지 않은 개체×시점(조사 미참여)은 모든 문항이 NaN 인 행으로 남는다.
    """
    ids = np.array(sorted(df[id_col].unique()))
    pos_i = {v: i for i, v in enumerate(ids)}
    pos_t = {v: t for t, v in enumerate(waves)}
    Y = np.full((len(ids), len(waves), len(items)), np.nan)
    sub = df[df[wave_col].isin(waves)]
    ii = sub[id_col].map(pos_i).to_numpy()
    tt = sub[wave_col].map(pos_t).to_numpy()
    Y[ii, tt, :] = sub[items].to_numpy(dtype=float)
    return Y, ids


# ---------------------------------------------------------------------------
# 2. E-step: scaled forward-backward
# ---------------------------------------------------------------------------
def _emission(YM, NM, theta):
    """B[n,t,k] = Π_j θ^y (1-θ)^(1-y), 결측 문항은 곱에서 제외(기여 1).

    YM = Y·M (관측된 1), NM = (1-Y)·M (관측된 0) 은 한 번만 계산해 넘겨받는다.
    """
    lt = np.log(theta)                           # (T,J,K)
    l1 = np.log1p(-theta)
    logB = np.empty((YM.shape[0], YM.shape[1], theta.shape[2]))
    for t in range(YM.shape[1]):
        logB[:, t] = YM[:, t] @ lt[t] + NM[:, t] @ l1[t]
    return np.exp(logB)


def estep(YM, NM, pi, A, theta, w=None):
    """사후확률 gamma[n,t,k], 구간별 전이 기대빈도 xi_sum[t,a,b], 로그우도를 돌려준다."""
    N, T, _ = YM.shape
    K = len(pi)
    if w is None:
        w = np.ones(N)
    B = _emission(YM, NM, theta)
    alpha = np.empty((N, T, K))
    c = np.empty((N, T))
    a = B[:, 0, :] * pi
    c[:, 0] = a.sum(1)
    alpha[:, 0] = a / c[:, [0]]
    for t in range(1, T):
        a = (alpha[:, t - 1] @ A[t - 1]) * B[:, t]
        c[:, t] = a.sum(1)
        alpha[:, t] = a / c[:, [t]]
    beta = np.ones((N, T, K))
    xi_sum = np.empty((T - 1, K, K))
    for t in range(T - 2, -1, -1):
        right = B[:, t + 1] * beta[:, t + 1] / c[:, [t + 1]]
        beta[:, t] = right @ A[t].T
        xi_sum[t] = ((alpha[:, t] * w[:, None]).T @ right) * A[t]
    gamma = alpha * beta
    gamma /= gamma.sum(2, keepdims=True)
    ind_ll = np.log(c).sum(1)
    return dict(gamma=gamma, xi_sum=xi_sum, loglik=float((w * ind_ll).sum()), ind_loglik=ind_ll)


# ---------------------------------------------------------------------------
# 3. 모수 개수, 초기값
# ---------------------------------------------------------------------------
def _groups(T, homog=False, a_groups=None):
    """구간 → 전이행렬 묶음 번호. 동질: 모두 0, 이질: 구간마다 다름, a_groups: 사용자가 정한 국면."""
    if a_groups is not None:
        g = np.asarray(a_groups, dtype=int)
        assert len(g) == T - 1
        return g
    return np.zeros(T - 1, dtype=int) if homog else np.arange(T - 1)


def _tgroups(t_groups, T, J):
    """응답확률 묶음을 (T, J) 배열로. 1차원이면 모든 문항에 같은 묶음, 2차원이면 문항별 묶음.

    예: 영상 문항(셋째)만 2024년부터 달라지게 하려면 np.zeros((6, 4), int) 에서 [4:, 2] = 1.
    """
    tg = np.asarray(t_groups, dtype=int)
    if tg.ndim == 1:
        tg = np.repeat(tg[:, None], J, axis=1)
    assert tg.shape == (T, J)
    return tg


def n_parameters(K, T, J, invariant=True, homog=False, a_groups=None, t_groups=None):
    """자유 모수 수 = 초기확률 + 전이확률 + 응답확률. t_groups 는 응답확률을 공유하는 시점 묶음(부분 측정불변)."""
    n_trans = len(np.unique(_groups(T, homog, a_groups))) * K * (K - 1)
    if invariant:
        n_resp = J * K
    elif t_groups is None:
        n_resp = J * K * T
    else:                                           # 문항별로 묶음 수가 다를 수 있다(부분 측정불변)
        tg2 = _tgroups(t_groups, T, J)
        n_resp = K * sum(len(np.unique(tg2[:, j])) for j in range(J))
    return (K - 1) + n_trans + n_resp


def random_init(K, T, J, rng):
    pi = np.full(K, 1.0 / K)
    A = np.empty((T - 1, K, K))
    for t in range(T - 1):
        m = rng.uniform(0.3, 1.0, (K, K)) + np.eye(K)
        A[t] = m / m.sum(1, keepdims=True)
    th = rng.uniform(0.08, 0.92, (J, K))
    theta = np.repeat(th[None], T, axis=0)
    return pi, A, theta


# ---------------------------------------------------------------------------
# 4. EM 한 번(초기값 하나)
# ---------------------------------------------------------------------------
def fit_once(Y, K, invariant=True, homog=False, maxit=3000, tol=1e-9, seed=1, init=None, w=None,
             a_groups=None, t_groups=None):
    """a_groups 예: [0,0,1,1] → 앞 두 구간과 뒤 두 구간이 각각 하나의 전이행렬을 공유(두 국면 모형)."""
    Y = np.asarray(Y, dtype=float)
    N, T, J = Y.shape
    M = (~np.isnan(Y)).astype(float)
    YM = np.nan_to_num(Y, nan=0.0) * M          # 관측된 1
    NM = M - YM                                  # 관측된 0
    YM2, M2 = YM.reshape(-1, J), M.reshape(-1, J)
    w = np.ones(N) if w is None else np.asarray(w, dtype=float)
    rng = np.random.default_rng(seed)
    if init is None:
        pi, A, theta = random_init(K, T, J, rng)
    else:
        pi, A, theta = (np.array(init[0], float), np.array(init[1], float), np.array(init[2], float))
        for gid in np.unique(_groups(T, homog, a_groups)):
            idx = _groups(T, homog, a_groups) == gid
            A[idx] = A[idx].mean(0)
        if invariant:
            theta = np.repeat(theta.mean(0, keepdims=True), T, axis=0)
    tg = None if (invariant or t_groups is None) else _tgroups(t_groups, T, J)   # 예: [0,0,0,0,1,1] → 앞 네 시점과 뒤 두 시점이 응답확률을 따로 가짐
    trace, converged = [], False
    wsum = w.sum()
    groups = _groups(T, homog, a_groups)
    for it in range(1, maxit + 1):
        e = estep(YM, NM, pi, A, theta, w)
        trace.append(e['loglik'])
        if it > 1 and abs(trace[-1] - trace[-2]) < tol * (1.0 + abs(trace[-1])):
            converged = True
            break
        if it == maxit:
            break
        g = e['gamma'] * w[:, None, None]
        # --- M-step ---
        pi = g[:, 0, :].sum(0) / wsum
        A = A.copy()
        for gid in np.unique(groups):                # 같은 묶음의 구간은 기대 전이빈도를 합쳐 추정
            idx = groups == gid
            cnt = e['xi_sum'][idx].sum(0)
            rs = cnt.sum(1, keepdims=True)
            A[idx] = np.where(rs > 1e-12, cnt / np.maximum(rs, 1e-300), A[idx][0])
        # 0에 수렴하는 확률이 비정규(denormal) 실수가 되어 연산이 느려지는 것을 막는다.
        pi = np.where(pi < 1e-15, 0.0, pi)
        pi = pi / pi.sum()
        A = np.where(A < 1e-15, 0.0, A)
        A = A / A.sum(2, keepdims=True)
        if invariant:
            g2 = g.reshape(-1, K)
            num = YM2.T @ g2
            den = M2.T @ g2
            th = np.where(den > 0, num / np.maximum(den, 1e-300), theta[0])
            theta = np.repeat(np.clip(th, CLIP, 1 - CLIP)[None], T, axis=0)
        else:
            num = np.einsum('ntk,ntj->tjk', g, YM)
            den = np.einsum('ntk,ntj->tjk', g, M)
            if tg is not None:                           # 같은 묶음의 시점은 분자·분모를 합쳐 추정
                for j in range(J):
                    for gid in np.unique(tg[:, j]):
                        idx = tg[:, j] == gid
                        num[idx, j], den[idx, j] = num[idx, j].sum(0), den[idx, j].sum(0)
            theta = np.clip(np.where(den > 0, num / np.maximum(den, 1e-300), theta), CLIP, 1 - CLIP)
    npar = n_parameters(K, T, J, invariant, homog, a_groups, None if invariant else t_groups)
    ll = e['loglik']
    return dict(K=K, invariant=invariant, homog=homog, a_groups=groups, pi=pi, A=A, theta=theta, loglik=ll,
                npar=npar, aic=-2 * ll + 2 * npar, bic=-2 * ll + np.log(wsum) * npar,
                gamma=e['gamma'], xi_sum=e['xi_sum'], trace=np.array(trace), iterations=it,
                converged=converged, n=float(wsum))


def order_states(fit):
    """상태 번호를 첫 시점 평균 응답확률의 오름차순으로 정렬한다(계산상의 라벨 규약)."""
    o = np.argsort(fit['theta'][0].mean(0), kind='stable')
    fit['pi'] = fit['pi'][o]
    fit['A'] = fit['A'][:, o][:, :, o]
    fit['theta'] = fit['theta'][:, :, o]
    fit['gamma'] = fit['gamma'][:, :, o]
    fit['xi_sum'] = fit['xi_sum'][:, o][:, :, o]
    return fit


# ---------------------------------------------------------------------------
# 5. 다중 초기값 적합
# ---------------------------------------------------------------------------
def fit(Y, K, n_starts=10, invariant=True, homog=False, maxit=3000, tol=1e-9, seed=1104,
        init=None, w=None, n_jobs=1, a_groups=None, t_groups=None):
    """초기값 n_starts 개로 EM 을 돌려 수렴한 해 중 로그우도가 가장 큰 것을 고른다.

    init 이 주어지면 첫 번째 시작값으로 사용한다(부트스트랩·몬테카를로의 warm start).
    반환값의 starts 는 초기값별 로그우도·수렴 여부·반복 수 기록이다.
    """
    Y = np.asarray(Y, dtype=float)
    N = Y.shape[0]
    # 같은 응답 궤적을 가진 개체를 하나로 묶고 빈도를 가중치로 쓴다(우도는 동일, 계산만 빨라짐).
    code = np.where(np.isnan(Y), -1.0, Y).reshape(N, -1)
    _, first, inverse = np.unique(code, axis=0, return_index=True, return_inverse=True)
    inverse = inverse.ravel()
    w_full = np.ones(N) if w is None else np.asarray(w, dtype=float)
    Yc = Y[first]
    wc = np.bincount(inverse, weights=w_full, minlength=len(first))

    def one(s):
        return fit_once(Yc, K, invariant, homog, maxit, tol, seed + s,
                        init if (s == 0 and init is not None) else None, wc, a_groups, t_groups)
    if n_jobs != 1 and n_starts > 1:
        from joblib import Parallel, delayed
        fits = Parallel(n_jobs=n_jobs)(delayed(one)(s) for s in range(n_starts))
    else:
        fits = [one(s) for s in range(n_starts)]
    ll = np.array([f['loglik'] for f in fits])
    ok = np.array([f['converged'] and np.isfinite(f['loglik']) for f in fits])
    pool = np.where(ok)[0] if ok.any() else np.arange(len(fits))
    best = fits[pool[np.argmax(ll[pool])]]
    best = order_states(best)
    best['gamma'] = best['gamma'][inverse]          # 묶었던 패턴을 개체 단위로 되돌림
    best['n_patterns'] = int(len(first))
    best['starts'] = [dict(start=i + 1, loglik=float(ll[i]), converged=bool(ok[i]),
                           iterations=int(fits[i]['iterations'])) for i in range(len(fits))]
    # 최고 로그우도가 다른 초기값에서도 재현된 횟수(국소해 점검)
    best['n_replicated'] = int(np.sum(np.abs(ll - best['loglik']) < 1e-6 * (1 + abs(best['loglik']))))
    return best


# ---------------------------------------------------------------------------
# 6. 사후 진단
# ---------------------------------------------------------------------------
def state_occupancy(pi, A):
    """모형이 함의하는 시점별 상태 비중 δ_t = π A_1 ... A_{t-1}."""
    out = [np.asarray(pi)]
    for t in range(A.shape[0]):
        out.append(out[-1] @ A[t])
    return np.array(out)


def classification_quality(Y, gamma):
    """한 문항 이상 관측된 개체×시점에서의 평균 최대 사후확률과 정규화 엔트로피(1=완전 분리)."""
    obs = (~np.isnan(Y)).any(2)
    g = gamma[obs]
    K = g.shape[1]
    if K == 1:
        return 1.0, 1.0
    ent = -(g * np.log(np.clip(g, 1e-300, 1))).sum(1)
    return float(g.max(1).mean()), float(1 - ent.mean() / np.log(K))


def bivariate_residuals(Y, fit_):
    """문항쌍×시점별 관측 2×2 빈도와 모형 기대빈도의 Pearson 불일치(BVR).

    조건부 독립 위반의 기술적 진단이며 p-value 로 읽지 않는다.
    """
    N, T, J = Y.shape
    delta = state_occupancy(fit_['pi'], fit_['A'])
    rows = []
    for t in range(T):
        th = fit_['theta'][t]
        for j in range(J):
            for l in range(j + 1, J):
                both = ~np.isnan(Y[:, t, j]) & ~np.isnan(Y[:, t, l])
                n = both.sum()
                if n == 0:
                    continue
                bvr = 0.0
                for a in (0, 1):
                    for b in (0, 1):
                        o = np.sum((Y[both, t, j] == a) & (Y[both, t, l] == b))
                        pj = th[j] if a else 1 - th[j]
                        pl = th[l] if b else 1 - th[l]
                        ex = n * float((delta[t] * pj * pl).sum())
                        bvr += (o - ex) ** 2 / max(ex, 1e-12)
                rows.append(dict(wave_index=t, item_a=j, item_b=l, n=int(n), bvr=float(bvr)))
    return rows


def lr_test(fit_restricted, fit_full):
    """포함관계 모형의 우도비 검정(카이제곱 근사)."""
    from scipy.stats import chi2
    stat = 2 * (fit_full['loglik'] - fit_restricted['loglik'])
    df = fit_full['npar'] - fit_restricted['npar']
    return dict(stat=float(stat), df=int(df), p=float(chi2.sf(max(stat, 0), df)))


# ---------------------------------------------------------------------------
# 7. 모의패널 생성(설계 보정 DGP)
# ---------------------------------------------------------------------------
def simulate_panel(N, pi, A, theta, rng, retention=None, reentry=0.30, item_missing=0.01,
                   buyer_items=(0, 1), buyer_penalty=0.05, nonbuyer_bonus=0.01):
    """잠재상태 경로와 이진 응답을 생성하고 조사 이탈·문항 무응답을 덧씌운다.

    retention[t] : 직전 시점 응답자가 t+1 시점에도 응답할 확률(공표 유지율로 보정).
    이탈은 직전 시점의 '관측된' 구매 응답에 의존한다(MAR): buyer_items 중 하나라도 1이면
    유지확률이 buyer_penalty 만큼 낮고, 아니면 nonbuyer_bonus 만큼 높다.
    """
    T = A.shape[0] + 1
    J, K = theta.shape[-2], theta.shape[-1]
    th = theta if theta.ndim == 3 else np.repeat(theta[None], T, axis=0)
    Z = np.empty((N, T), dtype=int)
    Z[:, 0] = rng.choice(K, size=N, p=pi)
    for t in range(1, T):
        cum = A[t - 1][Z[:, t - 1]].cumsum(1)
        Z[:, t] = (rng.random(N)[:, None] > cum).sum(1).clip(0, K - 1)
    P = np.stack([th[t][:, Z[:, t]].T for t in range(T)], axis=1)      # (N,T,J)
    Yfull = (rng.random((N, T, J)) < P).astype(float)
    Y = Yfull.copy()
    resp = np.ones((N, T), dtype=bool)
    if retention is not None:
        for t in range(1, T):
            prev = resp[:, t - 1]
            buyer = np.zeros(N, dtype=bool)
            for j in buyer_items:
                buyer |= (Yfull[:, t - 1, j] == 1) & prev
            p = np.where(prev, np.where(buyer, retention[t - 1] - buyer_penalty,
                                        retention[t - 1] + nonbuyer_bonus), reentry)
            resp[:, t] = rng.random(N) < np.clip(p, 0, 1)
    Y[~resp] = np.nan
    if item_missing > 0:
        Y[(rng.random(Y.shape) < item_missing)] = np.nan
    return Y, Z, resp
