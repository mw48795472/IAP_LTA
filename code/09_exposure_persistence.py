# -*- coding: utf-8 -*-
"""
09_exposure_persistence.py — 가격 인상 노출 지수와 구매 지속의 관계(지표 수준 로지스틱 회귀)

잠재상태 공변량 모형(08 스크립트 G절)이 원자료에서 불안정하였으므로, 같은 물음을 모형 가정이 적은 방식으로 다시 본다.
  물음: 가격 인상에 더 많이 노출된 사람이 가격 인상기에 구매를 더 많이 그만두었는가?
  자료: 2020년에 응답한 사람의 (t, t+1) 쌍. 기준 시점(2020년)의 노출 지수·운영체제·연령.
  모형: logit P(t+1 에 구입 | t 에 구입) = 구간 더미 + 노출 + 노출×가격 인상기 + 노출×이후 + 안드로이드 + 연령
        t 시점의 횡단 가중치, 가구 군집에 강건한 표준오차.
  관심 계수: 노출×가격 인상기. 음수이면 노출이 큰 사람이 가격 인상기에 덜 지속하였다는 뜻이다.

출력 outputs/real_exposure_logit.csv
"""
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import regulation_exposure as RX  # noqa: E402

WAVES = [2020, 2021, 2022, 2023, 2024, 2025]
panel = pd.read_csv(os.path.join(ROOT, 'data', 'private', 'consumer_panel.csv'))
RATES = RX.sector_price_increase()
b0 = panel[panel.wave == 2020].set_index('id')
b0 = b0[b0.android.notna() & b0.use_music.notna() & b0.use_webtoon.notna() & b0.ott_use.notna()]
use = np.column_stack([(b0.ott_use == 1).astype(float), b0.use_music, b0.use_webtoon, b0.use_game.fillna(0)])
b0 = b0.assign(expo=RX.exposure_index(use, RATES)['z'],
               expo_nv=RX.exposure_index(np.column_stack([np.zeros(len(b0)), b0.use_music, b0.use_webtoon, np.zeros(len(b0))]), RATES)['z'],
               age_z=(b0.age - b0.age.mean()) / b0.age.std())
hid0 = panel.sort_values('wave').groupby('id')['hid'].first()


def pairs(item):
    wide = panel.pivot(index='id', columns='wave', values=item)
    wt = panel.pivot(index='id', columns='wave', values='wt')
    out = []
    for t, (a, b) in enumerate(zip(WAVES[:-1], WAVES[1:])):
        m = wide[a].notna() & wide[b].notna() & wide.index.isin(b0.index)
        ids = wide.index[m]
        out.append(pd.DataFrame(dict(id=ids, interval=t, x0=wide.loc[ids, a].to_numpy(), y=wide.loc[ids, b].to_numpy(), w=wt.loc[ids, a].to_numpy())))
    d = pd.concat(out, ignore_index=True)
    d = d.join(b0[['expo', 'expo_nv', 'android', 'age_z']], on='id')
    d['hid'] = d['id'].map(hid0)
    d['hike'] = d.interval.isin([1, 2]).astype(float)
    d['post'] = d.interval.isin([3, 4]).astype(float)
    return d


rows = []
for item, label in (('inapp_item', '앱 내 아이템 구입'), ('paid_app', '유료 앱 구입'), ('paid_music', '음악 유료 이용')):
    d = pairs(item)
    for x0, kind in ((1, '지속(구입자)'), (0, '진입(비구입자)')):
        s = d[d.x0 == x0]
        for ex, tag in (('expo', '주 지수'), ('expo_nv', '영상 제외 지수')):
            X = pd.get_dummies(s.interval, prefix='iv', dtype=float)
            X['expo'] = s[ex]
            X['expo_x_hike'] = s[ex] * s.hike
            X['expo_x_post'] = s[ex] * s.post
            X['android'] = s.android
            X['age_z'] = s.age_z
            fit = sm.GLM(s.y, X, family=sm.families.Binomial(), var_weights=s.w).fit(cov_type='cluster', cov_kwds=dict(groups=s.hid.to_numpy()))
            for term, name in (('expo', '노출(이전 국면)'), ('expo_x_hike', '노출 × 가격 인상기'), ('expo_x_post', '노출 × 이후'), ('android', '안드로이드'), ('age_z', '연령(z)')):
                rows.append(dict(outcome=label, kind=kind, index=tag, term=name, estimate=fit.params[term], se=fit.bse[term], z=fit.tvalues[term], p=fit.pvalues[term],
                                 n=int(len(s)), n_persons=int(s.id.nunique()), n_households=int(s.hid.nunique())))
res = pd.DataFrame(rows)
res.to_csv(os.path.join(ROOT, 'outputs', 'real_exposure_logit.csv'), index=False, encoding='utf-8-sig')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 220)
print(res[res.term.isin(['노출(이전 국면)', '노출 × 가격 인상기', '노출 × 이후'])].round(3).to_string())
