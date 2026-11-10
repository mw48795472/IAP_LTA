# -*- coding: utf-8 -*-
"""
regulation_exposure.py — 규제 강도 변인의 정의

세 층으로 나눈다.
  1) 주 변인   개인별 가격 인상 노출 지수(exposure index)
               = Σ_s (기준 시점에 서비스 유형 s 를 이용했는가) × (유형 s 의 2022년 인앱 가격 인상률, %)
               지출액이 있으면 Σ_s (월평균 지출_s) × (인상률_s / 100) = 예상 추가 부담액(원/월)으로 바꿔 쓸 수 있다.
  2) 보조 변인 스마트폰 운영체제(안드로이드 = 1, iOS = 0).
               구글의 인앱결제 의무화(2022년 6월)로 결제 환경이 바뀐 쪽이 안드로이드다.
  3) 시기 통제 정책 단계(policy stage). 모든 사람에게 같은 값이므로 전이 절편(구간별 자유)으로 흡수하고,
               공변량 계수를 어느 구간끼리 묶을지(국면)를 정하는 데 쓴다.

인상률은 data/firm_strategy.csv 를 분석한 outputs/prop1_service_types.csv 에서 읽는다(실제 공개자료).
"""
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICES = ['video', 'music', 'webtoon', 'game']
SERVICE_LABELS = {'video': '영상(OTT) 유료', 'music': '음악', 'webtoon': '웹툰·웹소설·전자책', 'game': '게임'}
SECTOR_TO_SERVICE = {'영상': 'video', '음원': 'music', '웹툰·웹소설': 'webtoon', '게임': 'game'}

# 조사 연도별 정책 단계. 조사가 5~8월에 이루어지고 문항이 지난 1년을 묻기 때문에,
# 어느 해의 응답은 대략 전년도 중반부터 그해 중반까지의 경험이다.
POLICY_STAGE = {
    2019: 0, 2020: 0,
    2021: 0,   # 회상 기간 대부분이 법 시행(2021-09) 이전
    2022: 1,   # 법 시행·시행령(2022-03) 포함. 인앱결제 의무화와 가격 인상(2022-03~06)은 회상 기간의 끝
    2023: 2,   # 인앱결제 의무화와 가격 인상이 온전히 반영되는 첫 조사
    2024: 3,   # 시정조치안(2023-10) 이후
    2025: 3, 2026: 3,
    2027: 4,   # 과징금·시정명령(2026-10) 이후
}
STAGE_LABELS = {0: '법 시행 이전', 1: '법 시행, 의무화 직전', 2: '인앱결제 의무화와 가격 인상', 3: '시정조치안 이후', 4: '과징금·시정명령 이후'}


def sector_price_increase(csv_path=None):
    """서비스 유형별 2022년 안드로이드 인앱 가격 인상률의 중위값(%).

    게임은 인앱 가격을 올리지 않고 자체 결제 창구를 병행하였으므로 0으로 둔다.
    """
    import pandas as pd
    csv_path = csv_path or os.path.join(ROOT, 'outputs', 'prop1_service_types.csv')
    d = pd.read_csv(csv_path)
    d = d[d['android_price_change_date'].astype(str).str.startswith('2022') & d['price_change_pct'].notna()]
    med = d.groupby('sector')['price_change_pct'].median()
    rates = {s: 0.0 for s in SERVICES}
    for sector, service in SECTOR_TO_SERVICE.items():
        if sector in med.index:
            rates[service] = float(med[sector])
    return rates


def exposure_index(use, rates, spend=None):
    """가격 인상 노출 지수.

    use   : (N, 4) 기준 시점의 서비스 유형별 이용 여부(0/1), 열 순서는 SERVICES.
    spend : (N, 4) 기준 시점의 유형별 월평균 지출(원). 주면 예상 추가 부담액(원/월)을 계산한다.
    반환  : dict(raw=원 척도, z=표준화 값, mean=평균, sd=표준편차)
    """
    use = np.asarray(use, dtype=float)
    r = np.array([rates[s] for s in SERVICES])
    raw = use @ r if spend is None else (np.asarray(spend, dtype=float) * use) @ (r / 100.0)
    mean, sd = float(raw.mean()), float(raw.std())
    return dict(raw=raw, z=(raw - mean) / (sd if sd > 0 else 1.0), mean=mean, sd=sd)


def android_indicator(values):
    """운영체제 또는 제조사 문자열 → 안드로이드 1, iOS 0, 알 수 없으면 NaN."""
    out = np.full(len(values), np.nan)
    for i, v in enumerate(values):
        s = str(v).strip().lower()
        if s in ('1', '1.0', 'android', '안드로이드') or any(k in s for k in ('삼성', 'samsung', 'lg', '엘지', '샤오미', 'xiaomi', '구글', 'pixel')):
            out[i] = 1.0
        elif s in ('0', '0.0', 'ios') or any(k in s for k in ('애플', 'apple', 'iphone', '아이폰')):
            out[i] = 0.0
    return out


def policy_stage(wave):
    return POLICY_STAGE[int(wave)]


def coef_groups(waves, cut=2):
    """전이 구간(t → t+1)을 도착 시점의 정책 단계로 나눈 국면 번호. cut 이상이면 뒤 국면(1).

    waves = [2020..2024], cut=2 → [0, 0, 1, 1] (기본 사양), cut=1 → [0, 1, 1, 1] (경계를 한 구간 앞당긴 민감도 사양)
    """
    return [int(policy_stage(w) >= cut) for w in waves[1:]]


def build_covariates(cov_df, rates=None, id_order=None, use_spend=False):
    """실제 자료용: 기준 시점 공변량 표 → (N, 2) [노출 지수 z, 안드로이드].

    cov_df 의 열: id, use_video, use_music, use_webtoon, use_game, os_android
                 (선택) spend_video, spend_music, spend_webtoon, spend_game
    운영체제가 결측인 사람은 표본 평균으로 대체하지 않고 오류를 낸다(분석 대상에서 먼저 제외할 것).
    """
    rates = rates or sector_price_increase()
    d = cov_df.set_index('id')
    if id_order is not None:
        d = d.loc[list(id_order)]
    use = d[[f'use_{s}' for s in SERVICES]].to_numpy(dtype=float)
    spend = d[[f'spend_{s}' for s in SERVICES]].to_numpy(dtype=float) if use_spend else None
    ex = exposure_index(use, rates, spend)
    android = d['os_android'].to_numpy(dtype=float)
    if np.isnan(use).any() or np.isnan(android).any():
        raise ValueError('공변량에 결측이 있습니다. 기준 시점 공변량이 모두 있는 사람만 남기세요.')
    return np.column_stack([ex['z'], android]), ex
