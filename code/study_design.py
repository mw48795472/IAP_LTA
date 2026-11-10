# -*- coding: utf-8 -*-
"""
study_design.py — 모의패널의 설계값(DGP)을 한곳에 모아 둔 파일

중요: 아래 수치는 '가정한 설계값'이며 한국 이용자에 대한 추정치가 아니다.
  - 표본 크기와 유지율만 공표 자료(2025 한국미디어패널조사 보고서 <표 2-4>)에 맞췄다.
  - 상태별 응답확률은 2025년 공표 경험률(유료 앱 5.4%, 앱 내 아이템 15.4% 등)에
    마지막 시점의 문항 평균이 대략 맞도록 정했다(보정 목표이지 검증이 아니다).
  - 2022→2023 이후 구간의 '심어 둔 변화(DELTA)'는 추정 절차가 알려진 변화를
    되찾는지 시험하기 위한 가상의 시나리오다.
"""
import numpy as np

WAVES = [2020, 2021, 2022, 2023, 2024]
ITEMS = ['paid_app', 'inapp_item', 'paid_video', 'paid_music']
ITEM_LABELS = {'paid_app': '유료 앱 구입', 'inapp_item': '앱 내 아이템 구입',
               'paid_video': '영상(OTT) 유료 이용', 'paid_music': '음악 유료 이용'}
STATE_LABELS = ['S1 저소비', 'S2 구독 중심', 'S3 복합 구매']

# 2020년 통합패널 개인 응답자 수(공표값)
N_DESIGN = 10302
# 직전 연도 응답자 대비 유지율: 2021, 2022, 2023, 2024년(공표값, 통합패널)
RETENTION = np.array([0.946, 0.945, 0.948, 0.848])
REENTRY = 0.30          # 직전 연도 비응답자의 재응답 확률(가정)
ITEM_MISSING = 0.01     # 문항 무응답률(가정)

# 첫 시점(2020) 상태 비중(가정)
PI0 = np.array([0.55, 0.33, 0.12])

# 상태별 응답확률 theta[j,k] = P(문항 j = 1 | 상태 k) (가정, 시점 간 동일)
THETA = np.array([
    [0.005, 0.03, 0.30],   # paid_app
    [0.02,  0.10, 0.65],   # inapp_item
    [0.10,  0.85, 0.90],   # paid_video
    [0.03,  0.38, 0.70],   # paid_music
])

# 기준 연간 전이행렬(가정): 행 = 출발 상태, 열 = 도착 상태
A_BASE = np.array([
    [0.88, 0.10, 0.02],
    [0.06, 0.86, 0.08],
    [0.03, 0.12, 0.85],
])

DELTA_MAIN = 0.06       # 본 모의패널에 심어 둔 변화의 크기
SHIFT_INTERVALS = (2, 3)  # 0부터 센 구간 번호: 2022→2023, 2023→2024
SEED_MAIN = 20261106


def transition_matrices(delta=DELTA_MAIN):
    """구간별 전이행렬 (T-1, K, K). 변화 구간에서 S3→S2 확률을 delta 만큼 높인다."""
    A = np.repeat(A_BASE[None], len(WAVES) - 1, axis=0).copy()
    for t in SHIFT_INTERVALS:
        A[t, 2, 1] += delta
        A[t, 2, 2] -= delta
    return A


def theta_by_wave():
    return np.repeat(THETA[None], len(WAVES), axis=0)
