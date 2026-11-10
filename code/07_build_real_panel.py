# -*- coding: utf-8 -*-
"""
07_build_real_panel.py — 한국미디어패널 개인 원자료(2020~2025)를 분석용 long 형식으로 바꾼다.

입력  data/private/raw_kisdi/p{20..25}v32_KMP_csv.csv
      (KISDI 미디어통계포털 > 미디어패널조사 > 설문지·원시자료 > 원시자료 > 개인 > CSV, 이용 동의 후 내려받음)
출력  data/private/consumer_panel.csv        개인×연도 한 행(개인 자료이므로 코드집 ZIP에 넣지 않는다)
      outputs/real_variable_map.csv          지표별 원자료 변수
      outputs/real_prevalence_by_wave.csv    연도별 가중 경험률(공표값 재현 확인용 포함)
      outputs/real_sample_flow.csv           연도별 응답자 수와 유지

변수 대응은 코드북 없이 정했다. 각 변수의 가중 비율이 보고서 공표값과 소수 첫째 자리까지 일치하는지로 확인하였다
(예: 2025년 c06006 = 5.4%, c06007 = 15.4%, d26053 = 59.7%, c05051 = 28.0%).

지표의 정의(논문 <표 3>)
  paid_app    유료 애플리케이션 구입 경험(c06006 = 1). 스마트 기기 비이용자는 구입이 불가능하므로 0.
  inapp_item  앱 내 아이템·확장기능 구입 경험(c06007 = 1). 위와 같음.
  paid_video  OTT 월정액(d26053) 또는 건당 결제(d26052)를 이용하고 그 월평균 지출(d26057, d26055)이 양수. OTT 비이용자는 0.
              2020년 조사에는 지불 유형 문항이 없어 결측.
  paid_music  온라인 음악 이용(c05051 = 1)이고 월평균 지출(c05007)이 양수.
보조 정의
  *_na        비대상을 0이 아니라 결측으로 둔 것(민감도 분석용)
  sub_video   지출과 무관하게 월정액 또는 건당 결제 유형을 이용
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'private', 'raw_kisdi')
OUT = os.path.join(ROOT, 'outputs')
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
VARMAP = [
    ('paid_app', 'c06006', '유료 애플리케이션 구입 경험(1 있다, 2 없다). 스마트 기기 이용자만 응답'),
    ('inapp_item', 'c06007', '유/무료 애플리케이션 내 아이템 및 확장기능 구입 경험'),
    ('app_spend', 'c06010', '애플리케이션 관련 1년 총 지출(천원)'),
    ('ott_use', 'd26001', 'OTT 서비스 이용 여부'),
    ('ott_tvod', 'd26052', 'OTT 건당 결제형 이용(2021년부터)'),
    ('ott_svod', 'd26053', 'OTT 월정액제 가입형 이용(2021년부터)'),
    ('tvod_spend', 'd26055', '건당 결제형 월평균 지출(천원)'),
    ('svod_spend', 'd26057', '월정액제 가입형 월평균 지출(천원)'),
    ('use_edu', 'c05049', '온라인 교육 동영상 이용'),
    ('use_webtoon', 'c05050', '온라인 뉴스/잡지/E-book(웹툰·웹소설 포함) 이용'),
    ('use_music', 'c05051', '온라인 음악 이용'),
    ('use_game', 'c05052', '온라인 게임 이용'),
    ('webtoon_spend', 'c05001', '뉴스/잡지/E-book 월평균 지출(천원)'),
    ('music_spend', 'c05007', '음악 월평균 지출(천원)'),
    ('game_spend', 'c05009', '게임 월평균 지출(천원)'),
    ('phone_maker', 'a03028', '첫째 스마트폰 제조사(1 삼성, 2 LG, 3 애플, 그 밖은 기타)'),
    ('gender', 'gender', '성별(1 남, 2 여)'),
    ('age_group', 'age', '연령대(1 10대 미만 ~ 8 70세 이상)'),
    ('age', 'age1', '만 나이'),
]


def yes(x):
    """1 → 1, 2 → 0, 결측 → NaN"""
    return np.where(x == 1, 1.0, np.where(x == 2, 0.0, np.nan))


frames = []
for y in YEARS:
    yy = str(y)[2:]
    d = pd.read_csv(os.path.join(RAW, f'p{yy}v32_KMP_csv.csv'), encoding='cp949', low_memory=False, na_values=[' ', ''])
    g = pd.DataFrame({'id': d['pid'].astype(int), 'hid': d['hid'].astype(int), 'wave': y,
                      'wt': pd.to_numeric(d[f'p{yy}wt'], errors='coerce'), 'wt_long': pd.to_numeric(d[f'p{yy}wt2'], errors='coerce'),
                      'kmps19': d['KMPS19'].notna().astype(int)})
    for name, code, _ in VARMAP:
        col = f'p{yy}{code}'
        g[name] = pd.to_numeric(d[col], errors='coerce') if col in d.columns else np.nan
    smart = g['paid_app'].notna()                        # 스마트 기기 이용자(문항 응답 대상)
    ott = g['ott_use'] == 1
    g['smart_user'] = smart.astype(int)
    pa, ia = yes(g['paid_app']), yes(g['inapp_item'])
    g['paid_app_na'], g['inapp_item_na'] = pa, ia
    g['paid_app'], g['inapp_item'] = np.where(smart, pa, 0.0), np.where(smart, ia, 0.0)
    if y == 2020:
        g['paid_video'] = g['paid_video_na'] = g['sub_video'] = np.nan
    else:
        sv = (g['ott_svod'] == 1) & (g['svod_spend'].fillna(0) > 0)
        tv = (g['ott_tvod'] == 1) & (g['tvod_spend'].fillna(0) > 0)
        g['paid_video'] = (sv | tv).astype(float)
        g['paid_video_na'] = np.where(ott, g['paid_video'], np.nan)
        g['sub_video'] = ((g['ott_svod'] == 1) | (g['ott_tvod'] == 1)).astype(float)
    g['paid_music'] = ((g['use_music'] == 1) & (g['music_spend'].fillna(0) > 0)).astype(float)
    for c in ('use_edu', 'use_webtoon', 'use_music', 'use_game'):
        g[c] = yes(g[c])
    g['paid_webtoon'] = ((g['use_webtoon'] == 1) & (g['webtoon_spend'].fillna(0) > 0)).astype(float)
    g['android'] = np.where(g['phone_maker'].isna(), np.nan, (g['phone_maker'] != 3).astype(float))
    frames.append(g)
panel = pd.concat(frames, ignore_index=True)
assert not panel.duplicated(['id', 'wave']).any()
os.makedirs(os.path.join(ROOT, 'data', 'private'), exist_ok=True)
panel.to_csv(os.path.join(ROOT, 'data', 'private', 'consumer_panel.csv'), index=False, encoding='utf-8-sig')

pd.DataFrame(VARMAP, columns=['name', 'raw_code', 'description']).assign(
    raw_variable=lambda t: 'p{yy}' + t.raw_code).to_csv(os.path.join(OUT, 'real_variable_map.csv'), index=False, encoding='utf-8-sig')


def wmean(x, w):
    x = pd.Series(np.asarray(x, dtype=float), index=w.index)
    m = x.notna()
    return 100 * np.average(x[m], weights=w[m]) if m.any() and w[m].sum() > 0 else np.nan


rows = []
for y, g in panel.groupby('wave'):
    smart, ott = g.smart_user == 1, g.ott_use == 1
    rows.append(dict(
        wave=y, respondents=len(g),
        pub_paid_app_smart=wmean(g.paid_app_na, g.wt), pub_inapp_smart=wmean(g.inapp_item_na, g.wt),
        pub_svod_ott=wmean(yes(g.ott_svod.where(ott)), g.wt) if y > 2020 else np.nan, pub_music_use=wmean(g.use_music, g.wt),
        paid_app=wmean(g.paid_app, g.wt), inapp_item=wmean(g.inapp_item, g.wt), paid_video=wmean(g.paid_video, g.wt),
        paid_music=wmean(g.paid_music, g.wt), sub_video=wmean(g.sub_video, g.wt),
        paid_webtoon=wmean(g.paid_webtoon, g.wt), use_webtoon=wmean(g.use_webtoon, g.wt), use_game=wmean(g.use_game, g.wt),
        paid_game=wmean(((g.use_game == 1) & (g.game_spend.fillna(0) > 0)).astype(float), g.wt),
        app_spend_buyers_krw=1000 * np.average(g.app_spend.dropna(), weights=g.wt[g.app_spend.notna()]) if g.app_spend.notna().any() else np.nan,
        svod_spend_positive_share=wmean((g.svod_spend > 0).astype(float).where(g.ott_svod == 1), g.wt) if y > 2020 else np.nan,
        music_spend_positive_share=wmean((g.music_spend > 0).astype(float).where(g.use_music == 1), g.wt),
        webtoon_spend_positive_share=wmean((g.webtoon_spend > 0).astype(float).where(g.use_webtoon == 1), g.wt),
        game_spend_positive_share=wmean((g.game_spend > 0).astype(float).where(g.use_game == 1), g.wt),
        android_share=wmean(g.android, g.wt), unweighted_inapp=100 * g.inapp_item.mean(), unweighted_paid_video=100 * g.paid_video.mean()))
prev = pd.DataFrame(rows).round(2)
prev.to_csv(os.path.join(OUT, 'real_prevalence_by_wave.csv'), index=False, encoding='utf-8-sig')

wide = panel.pivot(index='id', columns='wave', values='wt').notna()
flow = []
for i, y in enumerate(YEARS):
    r = dict(wave=y, respondents=int(wide[y].sum()))
    if i:
        prev_y = YEARS[i - 1]
        r['retained_from_prev'] = int((wide[y] & wide[prev_y]).sum())
        r['retention_pct'] = round(100 * r['retained_from_prev'] / wide[prev_y].sum(), 1)
        r['new_or_returning'] = int((wide[y] & ~wide[prev_y]).sum())
    flow.append(r)
flow = pd.DataFrame(flow)
flow.to_csv(os.path.join(OUT, 'real_sample_flow.csv'), index=False, encoding='utf-8-sig')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250)
print('persons', panel.id.nunique(), 'person-waves', len(panel), 'households', panel.hid.nunique(),
      'all six waves', int(wide.all(axis=1).sum()), '2021-2025 all', int(wide[[2021, 2022, 2023, 2024, 2025]].all(axis=1).sum()))
print(prev.T.to_string())
print(flow.to_string())
