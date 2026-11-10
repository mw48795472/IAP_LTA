# -*- coding: utf-8 -*-
"""
10_real_transition_figure.py — 원자료에서 추정한 구간별 전이행렬 그림

모의자료의 <그림 6>과 같은 모양으로, 한국미디어패널 개인 원자료 2020~2025년의 주 모형 추정값을 그린다.
입력  outputs/real_transition_probabilities.csv (08_real_data_lta.py 가 만든 집계 결과. 개인 자료는 필요 없다)
출력  figures/fig14_real_transition_matrices.png          논문 <그림 14>(읽는 법 설명 포함)
      figures/real_transition_matrices_plain.png          --plain: 설명 칸 없이 행렬만(논문·발표자료에는 쓰지 않는 별도 그림)

실행: python code/10_real_transition_figure.py [--plain]
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

PLAIN = '--plain' in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tr = pd.read_csv(os.path.join(ROOT, 'outputs', 'real_transition_probabilities.csv'))
SL = ['S1 저소비', 'S2 구독 중심', 'S3 복합 구매']
IV = list(dict.fromkeys(tr.interval))
HIKE = {'2021→2022', '2022→2023'}                 # 인앱결제 의무화와 가격 인상이 회상 기간에 들어가는 구간

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
INK, MUTED, ORANGE = '#1f2937', '#6b7280', '#eb6834'
cmap = LinearSegmentedColormap.from_list('blues', ['#eef3fb', '#c9daf2', '#8fb5e6', '#2a78d6', '#174a8f'])


def draw(ax, iv, ylabels):
    q = tr[tr.interval == iv]
    get = lambda col: np.array([[q[(q.from_state == a) & (q.to_state == b)][col].iloc[0] for b in SL] for a in SL])   # noqa: E731
    est, lo, hi = get('estimate'), get('lo'), get('hi')
    ax.pcolormesh(est, cmap=cmap, vmin=0, vmax=1, edgecolors='white', linewidth=3)   # 칸 사이를 흰 선으로 띄운다
    ax.set_xlim(0, 3)
    ax.set_ylim(3, 0)
    for a in range(3):
        for b in range(3):
            dark = est[a, b] >= 0.72                     # 진한 칸에서만 흰 글자(대비 확보)
            ax.text(b + 0.5, a + 0.40, f'{est[a, b]:.3f}', ha='center', va='center', fontsize=13, fontweight='bold', color='white' if dark else INK)
            ax.text(b + 0.5, a + 0.74, f'({lo[a, b]:.3f}–{hi[a, b]:.3f})', ha='center', va='center', fontsize=8.5,
                    color='white' if dark else (INK if est[a, b] >= 0.4 else MUTED))
    ax.tick_params(which='both', length=0)
    ax.set_xticks(np.arange(3) + 0.5)
    ax.set_xticklabels(SL, fontsize=9.5, color=INK)
    ax.set_yticks(np.arange(3) + 0.5)
    ax.set_yticklabels(SL if ylabels else [], fontsize=9.5, color=INK)
    ax.set_xlabel('도착 상태', fontsize=10.5, color=INK)
    if ylabels:
        ax.set_ylabel('출발 상태', fontsize=11, color=INK)
    for s in ax.spines.values():
        s.set_visible(False)
    hike = iv in HIKE
    # 별도 그림(--plain)에서는 가격 인상기를 글자 없이 제목 색으로만 구분한다
    ax.set_title(iv.replace('→', ' → ') + ('  가격 인상기' if hike and not PLAIN else ''), fontsize=12, color=ORANGE if hike else INK, fontweight='bold' if hike else 'normal', pad=8)


FOOT = '한국미디어패널 개인 원자료 2020~2025년(11,362명) · 실제 추정치'
if PLAIN:
    # 설명 칸 없이 행렬 다섯 개만: 윗줄 셋, 아랫줄 둘(가운데 정렬)
    fig = plt.figure(figsize=(12.4, 8.0))
    gs = fig.add_gridspec(2, 6, left=0.09, right=0.985, top=0.94, bottom=0.10, wspace=0.12, hspace=0.42)
    slots = [gs[0, 0:2], gs[0, 2:4], gs[0, 4:6], gs[1, 1:3], gs[1, 3:5]]
    for k, (slot, iv) in enumerate(zip(slots, IV)):
        draw(fig.add_subplot(slot), iv, ylabels=k in (0, 3))
    fig.text(0.985, 0.012, FOOT + ' · 괄호 안은 가구 군집 부트스트랩 95% 구간', fontsize=9, color=MUTED, ha='right', va='bottom')
    out = 'real_transition_matrices_plain.png'
else:
    fig, axes = plt.subplots(2, 3, figsize=(12.4, 8.0))
    for k, (ax, iv) in enumerate(zip(axes.ravel(), IV)):
        draw(ax, iv, ylabels=k in (0, 3))
    note = axes[1, 2]
    note.axis('off')
    note.text(0.02, 0.92, '읽는 법', fontsize=11.5, fontweight='bold', color=INK, va='top', transform=note.transAxes)
    note.text(0.02, 0.80, '각 칸은 왼쪽 상태에 있던 사람이 다음 해에\n위쪽 상태에 있을 확률이다.\n대각선은 같은 상태에 머물 확률.\n\n'
              '괄호 안은 가구 단위로 재표집한\n부트스트랩 95% 구간(300회).\n\n'
              '영상 문항의 응답확률만 2024년부터\n따로 추정한 세 상태 모형, 가중 추정.\n\n'
              '시기에 따른 차이는 규제의 인과효과가 아니다.',
              fontsize=9.5, color=MUTED, va='top', linespacing=1.5, transform=note.transAxes)
    fig.text(0.985, 0.012, FOOT, fontsize=9, color=MUTED, ha='right', va='bottom')
    fig.subplots_adjust(left=0.09, right=0.985, top=0.94, bottom=0.10, wspace=0.05, hspace=0.42)
    out = 'fig14_real_transition_matrices.png'
fig.savefig(os.path.join(ROOT, 'figures', out), dpi=170)
print('saved', out)
