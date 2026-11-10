# -*- coding: utf-8 -*-
"""
13_real_s3_transition_table.py — 복합 구매 상태에서 출발하는 구간별 전이확률 표(원자료)

모의자료의 '참값·추정값·95% 구간' 표(<표 13>)에 대응한다. 원자료에는 참값이 없으므로 추정값과 구간만 적는다.
입력  outputs/real_transition_probabilities.csv (08_real_data_lta.py 의 집계 결과)
출력  figures/real_s3_transition_table.png, outputs/real_s3_transition_table.csv
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tr = pd.read_csv(os.path.join(ROOT, 'outputs', 'real_transition_probabilities.csv'))
SL = ['S1 저소비', 'S2 구독 중심', 'S3 복합 구매']
s3 = tr[tr.from_state == SL[2]].copy()
s3['ci'] = s3.apply(lambda r: f'{r.lo:.3f} ~ {r.hi:.3f}', axis=1)
out = s3[['interval', 'to_state', 'estimate', 'lo', 'hi']].rename(columns=dict(interval='구간', to_state='도착 상태', estimate='추정값', lo='95% 구간 하한', hi='95% 구간 상한'))
out.to_csv(os.path.join(ROOT, 'outputs', 'real_s3_transition_table.csv'), index=False, encoding='utf-8-sig')

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
INK, MUTED, RULE, BAND, ORANGE = '#1f2937', '#6b7280', '#9ca3af', '#f3f6fa', '#eb6834'
HIKE = {'2021→2022', '2022→2023'}
IV = list(dict.fromkeys(s3.interval))
n = len(s3)
rh = 0.40
W, H = 8.6, 1.2 + (n + 1) * rh + 0.85
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
x0, x1 = 0.45, W - 0.45
cx = dict(iv=x0 + 0.1, dest=2.55, est=5.35, ci=7.0)
top = H - 1.2
ax.text(x0, H - 0.50, '복합 구매 상태에서 출발하는 연간 전이확률', fontsize=14, fontweight='bold', color=INK, va='center')
ax.text(x0, H - 0.88, '한국미디어패널 개인 원자료 2020~2025년, 11,362명 · 실제 추정값', fontsize=9.5, color=MUTED, va='center')
ax.plot([x0, x1], [top, top], color=INK, lw=1.6)
yh = top - rh / 2
ax.text(cx['iv'], yh, '구간', fontsize=11, fontweight='bold', color=INK, va='center')
ax.text(cx['dest'], yh, '도착 상태', fontsize=11, fontweight='bold', color=INK, va='center')
ax.text(cx['est'], yh, '추정값', fontsize=11, fontweight='bold', color=INK, va='center', ha='center')
ax.text(cx['ci'], yh, '95% 구간', fontsize=11, fontweight='bold', color=INK, va='center', ha='center')
ax.plot([x0, x1], [top - rh, top - rh], color=INK, lw=0.9)
i = 0
for iv in IV:
    q = s3[s3.interval == iv]
    hike = iv in HIKE
    for k, (_, r) in enumerate(q.iterrows()):
        y = top - rh * (i + 1.5)
        if k == 0 and i > 0:
            ax.plot([x0, x1], [y + rh / 2, y + rh / 2], color=RULE, lw=0.7)
        if hike:
            ax.add_patch(plt.Rectangle((x0, y - rh / 2), x1 - x0, rh, color=BAND, lw=0, zorder=0))
        if k == 0:
            ax.text(cx['iv'], y, iv.replace('→', ' → '), fontsize=10.5, color=ORANGE if hike else INK, fontweight='bold' if hike else 'normal', va='center')
        stay = r.to_state == SL[2]
        ax.text(cx['dest'], y, r.to_state, fontsize=10.5, color=INK, va='center')
        ax.text(cx['est'], y, f'{r.estimate:.3f}', fontsize=10.5, color=INK, va='center', ha='center', fontweight='bold' if stay else 'normal')
        ax.text(cx['ci'], y, r.ci, fontsize=10.5, color=INK, va='center', ha='center')
        i += 1
bot = top - rh * (n + 1)
ax.plot([x0, x1], [bot, bot], color=INK, lw=1.6)
ax.text(x0, bot - 0.20, '주: 세 상태, 영상 문항만 2024년부터 응답확률을 따로 둔 모형, 가중 추정. 95% 구간은 가구 군집 부트스트랩 300회.\n'
        '굵은 숫자는 복합 구매 상태에 머물 확률. 주황색 구간은 인앱결제 의무화와 가격 인상이 걸친 구간. 원자료이므로 참값은 없다.',
        fontsize=8.5, color=MUTED, va='top', linespacing=1.5)
fig.savefig(os.path.join(ROOT, 'figures', 'real_s3_transition_table.png'), dpi=180)
print(out.round(3).to_string(index=False))
