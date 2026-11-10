# -*- coding: utf-8 -*-
"""
11_real_parameter_table.py — 모의패널 설계값 표(<표 4>)에 대응하는 원자료 추정값 표

<표 4>는 모의패널을 만들 때 가정한 값이다. 이 스크립트는 같은 틀에 한국미디어패널 개인 원자료 2020~2025년의
주 모형 추정값을 넣어 표로 그린다. 원자료에서는 전이확률이 구간마다 달랐으므로 세 국면의 평균으로 제시하고,
영상 문항은 2024년 전후의 응답확률을 따로 적는다.

입력  outputs/real_summary.json (08_real_data_lta.py 가 만든 집계 결과. 개인 자료는 필요 없다)
출력  figures/real_parameter_table.png, outputs/real_parameter_table.csv
"""
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rs = json.load(open(os.path.join(ROOT, 'outputs', 'real_summary.json'), encoding='utf-8'))
m = rs['main']
A = np.array(m['A'])                     # (구간 5, 출발 3, 도착 3)
th0, th1 = np.array(m['theta_2020_2023']), np.array(m['theta_2024_2025'])
occ = np.array(m['occupancy'])
SL = ['S1 저소비', 'S2 구독 중심', 'S3 복합 구매']
REG = [('이전(2020→2021년)', [0]), ('가격 인상기(2021→2023년)', [1, 2]), ('이후(2023→2025년)', [3, 4])]

rows = [('상태 비중', '2020년 상태 비중', occ[0])]
rows += [('응답확률', '유료 앱 구입', th0[0]), ('응답확률', '앱 내 아이템 구입', th0[1]),
         ('응답확률', '영상 유료 이용(2021~2023년)', th0[2]), ('응답확률', '영상 유료 이용(2024~2025년)', th1[2]),
         ('응답확률', '음악 유료 이용', th0[3])]
for a in range(3):
    for name, idx in REG:
        rows.append((f'연간 전이확률: {SL[a].split()[0]}에서', name, A[idx, a, :].mean(0)))
tab = pd.DataFrame([dict(block=b, row=r, **{SL[k]: float(v[k]) for k in range(3)}) for b, r, v in rows])
tab.to_csv(os.path.join(ROOT, 'outputs', 'real_parameter_table.csv'), index=False, encoding='utf-8-sig')

# ---------------------------------------------------------------------------
# 표 그림(위·아래 굵은 선, 머리글 아래와 묶음 사이 가는 선)
# ---------------------------------------------------------------------------
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
INK, MUTED, RULE, BAND, ORANGE = '#1f2937', '#6b7280', '#9ca3af', '#f3f6fa', '#eb6834'
n = len(rows)
rh = 0.42                                  # 행 높이(인치)
W, H = 9.6, 1.2 + (n + 1) * rh + 0.85
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis('off')
x0, x1 = 0.45, W - 0.45
cx = [5.55, 7.05, 8.5]                     # 숫자 열의 가운데
top = H - 1.2
ax.text(x0, H - 0.50, '원자료에서 추정한 상태 비중, 응답확률, 전이확률', fontsize=14, fontweight='bold', color=INK, va='center')
ax.text(x0, H - 0.88, f"한국미디어패널 개인 원자료 2020~2025년, {rs['n_persons']:,}명 · 모의패널 설계값 표에 대응하는 실제 추정값", fontsize=9.5, color=MUTED, va='center')
ax.plot([x0, x1], [top, top], color=INK, lw=1.6)
yh = top - rh / 2
ax.text(x0 + 0.1, yh, '구분', fontsize=11, fontweight='bold', color=INK, va='center')
for c, s in zip(cx, SL):
    ax.text(c, yh, s, fontsize=11, fontweight='bold', color=INK, va='center', ha='center')
ax.plot([x0, x1], [top - rh, top - rh], color=INK, lw=0.9)
prev_block = None
for i, (block, label, v) in enumerate(rows):
    y = top - rh * (i + 1.5)
    if block != prev_block and i > 0:
        ax.plot([x0, x1], [y + rh / 2, y + rh / 2], color=RULE, lw=0.7)
    hike = label.startswith('가격 인상기')
    if hike:
        ax.add_patch(plt.Rectangle((x0, y - rh / 2), x1 - x0, rh, color=BAND, lw=0, zorder=0))
    first = block != prev_block
    if block.startswith('연간'):
        if first:
            ax.text(x0 + 0.1, y, block, fontsize=10.5, color=INK, va='center')
        ax.text(x0 + 2.55, y, label, fontsize=10, color=ORANGE if hike else MUTED, va='center', fontweight='bold' if hike else 'normal')
    else:
        ax.text(x0 + 0.1, y, label if block == '상태 비중' else f'{block}: {label}', fontsize=10.5, color=INK, va='center')
    for k, c in enumerate(cx):
        stay = block.startswith('연간') and k == int(block.split('S')[1][0]) - 1      # 같은 상태에 머물 확률
        ax.text(c, y, f'{v[k]:.3f}', fontsize=10.5, color=INK, va='center', ha='center', fontweight='bold' if stay else 'normal')
    prev_block = block
bot = top - rh * (n + 1)
ax.plot([x0, x1], [bot, bot], color=INK, lw=1.6)
ax.text(x0, bot - 0.20, '주: 세 상태, 영상 문항만 2024년부터 응답확률을 따로 둔 부분 측정불변 모형, 가중 추정. 전이확률은 국면에 속한 구간의 평균이며\n'
        '굵은 숫자는 같은 상태에 머물 확률. 2020년 조사에는 영상의 지불 유형 문항이 없다. 시기에 따른 차이는 규제의 인과효과가 아니다.',
        fontsize=8.5, color=MUTED, va='top', linespacing=1.5)
fig.savefig(os.path.join(ROOT, 'figures', 'real_parameter_table.png'), dpi=180)
print(tab.round(3).to_string())
