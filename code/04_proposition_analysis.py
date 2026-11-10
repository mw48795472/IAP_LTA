# -*- coding: utf-8 -*-
"""04_proposition_analysis.py — 연구명제 1·2의 공개자료 분석

연구명제 1: 규제 시행 전후 앱마켓 관련 기업의 사업·결제전략 유형에 변화가 나타날 것이다.
연구명제 2: 플랫폼 사업자의 전략적 대응에 따라 규제의 실질적 효과는 정책목표와 다르게 나타날 수 있다.

입력(모두 공개 보도·공식 문서에서 손으로 코딩한 자료, 출처 URL 포함)
  data/firm_strategy.csv                 서비스별 규제 전후 안드로이드 결제 방식과 대표 상품 가격
  data/policy_goal_outcome_evidence.csv  정책목표별 결과 지표
출력
  outputs/prop1_service_types.csv        서비스별 전략 유형과 가격 변화, 손익분기 수수료율
  outputs/prop1_crosstab.csv             규제 전 결제 방식 × 규제 후 전략 유형
  outputs/prop1_summary.json             비율·정확 신뢰구간·정확 검정
  figures/fig09_strategy_shift.png
실행: python code/04_proposition_analysis.py
주의: 표본은 보도로 확인된 서비스의 편의표본이다. 검정과 신뢰구간은 기술 통계의 보조 수단으로만 읽는다.
"""
import json
from pathlib import Path

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DATA, OUT, FIG = ROOT / 'data', ROOT / 'outputs', ROOT / 'figures'

mpl.rcParams.update({
    'font.family': 'Malgun Gothic', 'axes.unicode_minus': False, 'savefig.dpi': 200,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#8a8983',
    'axes.grid': True, 'grid.color': '#e6e5e0', 'grid.linewidth': 0.8, 'axes.axisbelow': True,
    'axes.labelcolor': '#52514e', 'xtick.color': '#52514e', 'ytick.color': '#52514e',
    'text.color': '#0b0b0b', 'font.size': 10, 'axes.titlesize': 11, 'legend.frameon': False,
    'figure.facecolor': 'white', 'axes.facecolor': 'white'})
BLUE, ORANGE, INK2 = '#2a78d6', '#eb6834', '#52514e'

PRE_LABEL = {'own_billing': '앱 내 자체결제', 'google_iap': '구글 인앱결제', 'web_only': '앱 내 결제 없음(웹 전용)', 'mixed': '혼합'}
POST_ORDER = ['인앱결제 수용·가격 인상', '인앱결제 수용·가격 유지', '인앱결제 수용·가격 변화 미확인', '제3자 결제 도입', '인앱결제 유지·자체 채널 병행', '앱 내 결제 제거(웹 전용)']


def post_type(row):
    """규제 후 전략 유형: 결제 방식과 인앱 가격 인상 여부를 묶어 분류한다."""
    pay, up = row['post_android_payment'], row['price_up']
    if pay == 'third_party_billing':
        return '제3자 결제 도입'
    if pay == 'web_only':
        return '앱 내 결제 제거(웹 전용)'
    if pay == 'mixed':
        return '인앱결제 유지·자체 채널 병행'
    if pay == 'google_iap':
        if up is True:
            return '인앱결제 수용·가격 인상'
        return '인앱결제 수용·가격 유지' if up is False else '인앱결제 수용·가격 변화 미확인'
    return np.nan


def clopper_pearson(k, n, level=0.95):
    a = 1 - level
    lo = 0.0 if k == 0 else stats.beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else stats.beta.ppf(1 - a / 2, k + 1, n - k)
    return float(lo), float(hi)


def share(k, n):
    lo, hi = clopper_pearson(k, n) if n else (np.nan, np.nan)
    return {'k': int(k), 'n': int(n), 'share': (k / n if n else None), 'ci95': [lo, hi]}


def main():
    raw = pd.read_csv(DATA / 'firm_strategy.csv', encoding='utf-8-sig', dtype=str).apply(lambda s: s.str.strip())
    raw = raw.replace({'': np.nan})
    for col in ('android_price_old_krw', 'android_price_new_krw'):
        raw[col] = pd.to_numeric(raw[col].str.replace(',', ''), errors='coerce')
    market = raw[raw['sector'] == '앱마켓'].copy()
    d = raw[raw['sector'] != '앱마켓'].copy()

    # ── 가격 변화와 손익분기 수수료율 ──────────────────────────────────────────
    # 인상률 r = P_new/P_old − 1.  수수료율 f를 물고도 건당 순수입이 같으려면 P_new(1−f) = P_old,
    # 곧 f* = 1 − P_old/P_new.  f*가 실제 수수료율(구독 15%, 그 밖 30%)과 같으면 수수료를 전액 가격에 전가한 것이다.
    d['price_change_pct'] = 100 * (d['android_price_new_krw'] / d['android_price_old_krw'] - 1)
    d['breakeven_fee_pct'] = 100 * (1 - d['android_price_old_krw'] / d['android_price_new_krw'])
    d['price_up'] = d['price_change_pct'].map(lambda x: np.nan if pd.isna(x) else bool(x > 0)).astype(object)
    d['pre_type'] = d['pre_android_payment'].map(PRE_LABEL)
    d['post_type'] = d.apply(post_type, axis=1)
    d['uses_iap_pre'] = d['pre_android_payment'].isin(['google_iap', 'mixed'])
    d['uses_iap_post'] = d['post_android_payment'].isin(['google_iap', 'mixed'])
    d['payment_changed'] = d['pre_android_payment'] != d['post_android_payment']

    coded = d.dropna(subset=['pre_android_payment', 'post_android_payment']).copy()
    # 가격 분석은 구글 정책 전환기(2022년)의 변경만 포함한다. 그 밖의 시점(예: 유튜브 프리미엄 2023-12)은 표에만 남긴다.
    d['in_2022_window'] = d['android_price_change_date'].fillna('').str.startswith('2022')
    priced = d.dropna(subset=['price_change_pct'])
    priced_other = priced[~priced['in_2022_window']].copy()
    priced = priced[priced['in_2022_window']].copy()

    cols = ['firm', 'service', 'sector', 'pre_type', 'post_type', 'payment_changed', 'android_price_old_krw',
            'android_price_new_krw', 'price_product', 'android_price_change_date', 'price_change_pct',
            'breakeven_fee_pct', 'web_price_kept', 'verification', 'source_url_1']
    d[cols].to_csv(OUT / 'prop1_service_types.csv', index=False, encoding='utf-8-sig', float_format='%.2f')

    ct = pd.crosstab(coded['pre_type'], coded['post_type'], margins=True, margins_name='합계')
    ct = ct.reindex(columns=[c for c in POST_ORDER if c in ct.columns] + ['합계'])
    ct.to_csv(OUT / 'prop1_crosstab.csv', encoding='utf-8-sig')

    # ── 정확 검정 ─────────────────────────────────────────────────────────────
    # (1) 구글 인앱결제 사용 여부의 전후 변화: 맥니마 정확 검정(불일치 쌍의 이항 검정)
    b = int((~coded['uses_iap_pre'] & coded['uses_iap_post']).sum())      # 미사용 → 사용
    c = int((coded['uses_iap_pre'] & ~coded['uses_iap_post']).sum())      # 사용 → 미사용
    mcnemar_p = float(stats.binomtest(b, b + c, 0.5).pvalue) if b + c else None
    # (2) 인앱 가격: 인상·인하 부호 검정, 로그 가격비의 윌콕슨 부호순위 검정
    up, down = int((priced['price_change_pct'] > 0).sum()), int((priced['price_change_pct'] < 0).sum())
    sign_p = float(stats.binomtest(up, up + down, 0.5).pvalue) if up + down else None
    logratio = np.log(priced['android_price_new_krw'] / priced['android_price_old_krw'])
    wil_p = float(stats.wilcoxon(logratio[logratio != 0]).pvalue) if (logratio != 0).sum() >= 5 else None

    raised = priced[priced['price_change_pct'] > 0]
    webkept = d.dropna(subset=['web_price_kept'])
    summary = {
        'n_services': int(len(d)), 'n_coded_payment': int(len(coded)), 'n_priced': int(len(priced)),
        'n_market_operators': int(len(market)),
        'priced_outside_2022': priced_other[['service', 'android_price_change_date', 'price_change_pct']].to_dict('records'),
        'verification_counts': d['verification'].value_counts(dropna=False).to_dict(),
        'payment_changed': share(int(coded['payment_changed'].sum()), len(coded)),
        'iap_use_pre': share(int(coded['uses_iap_pre'].sum()), len(coded)),
        'iap_use_post': share(int(coded['uses_iap_post'].sum()), len(coded)),
        'third_party_adopted': share(int((coded['post_android_payment'] == 'third_party_billing').sum()), len(coded)),
        'mcnemar': {'not_to_iap': b, 'iap_to_not': c, 'p_exact': mcnemar_p},
        'price_raised': share(up, len(priced)),
        'sign_test_p': sign_p, 'wilcoxon_p': wil_p,
        'price_change_pct_raised': {k: float(getattr(raised['price_change_pct'], k)()) for k in ('mean', 'median', 'min', 'max')} if len(raised) else None,
        'breakeven_fee_pct_raised': {k: float(getattr(raised['breakeven_fee_pct'], k)()) for k in ('mean', 'median', 'min', 'max')} if len(raised) else None,
        'full_passthrough_rise_pct': {'fee15': 100 * 0.15 / 0.85, 'fee30': 100 * 0.30 / 0.70},
        'web_price_kept': share(int((webkept['web_price_kept'] == 'Y').sum()), len(webkept)),
        'post_type_counts': coded['post_type'].value_counts().to_dict(),
        'pre_type_counts': coded['pre_type'].value_counts().to_dict(),
        'sector_counts': d['sector'].value_counts().to_dict(),
    }
    (OUT / 'prop1_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    # ── 그림 9 ────────────────────────────────────────────────────────────────
    # 인쇄 가독성을 위해 세로 2단(본문 폭 기준 글자 크기 확보)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.6, 8.6), gridspec_kw={'height_ratios': [1, 1.35], 'hspace': 0.45})
    modes = ['own_billing', 'google_iap', 'third_party_billing', 'web_only', 'mixed']
    names = ['앱 내 자체결제', '구글 인앱결제', '제3자 결제', '앱 내 결제 없음\n(웹 전용)', '인앱결제+자체\nPC·웹 결제']
    pre_n = [int((coded['pre_android_payment'] == m).sum()) for m in modes]
    post_n = [int((coded['post_android_payment'] == m).sum()) for m in modes]
    keep = [i for i in range(len(modes)) if pre_n[i] + post_n[i] > 0]
    y = np.arange(len(keep))[::-1]
    ax1.barh(y + 0.19, [pre_n[i] for i in keep], height=0.34, color=BLUE, label='규제 전(~2021년)')
    ax1.barh(y - 0.19, [post_n[i] for i in keep], height=0.34, color=ORANGE, label='규제 후(2022년 6월~)')
    for yy, i in zip(y, keep):
        ax1.text(pre_n[i] + 0.15, yy + 0.19, str(pre_n[i]), va='center', fontsize=9, color=INK2)
        ax1.text(post_n[i] + 0.15, yy - 0.19, str(post_n[i]), va='center', fontsize=9, color=INK2)
    ax1.set_yticks(y, [names[i] for i in keep])
    ax1.set_xlabel('서비스 수')
    ax1.set_xlim(0, max(pre_n + post_n) + 1.5)
    ax1.xaxis.set_major_locator(mpl.ticker.MaxNLocator(integer=True))
    ax1.grid(axis='y', visible=False)
    ax1.set_title(f'(가) 안드로이드 앱의 결제 방식 (n = {len(coded)})', loc='left')
    ax1.legend(loc='lower right', fontsize=9)

    p = priced.sort_values('price_change_pct')
    yy = np.arange(len(p))
    ax2.hlines(yy, 0, p['price_change_pct'], color=ORANGE, linewidth=2)
    ax2.plot(p['price_change_pct'], yy, 'o', color=ORANGE, markersize=7, markeredgecolor='white', markeredgewidth=1.2)
    r15, r30 = 100 * 0.15 / 0.85, 100 * 0.30 / 0.70
    for v, k in zip(p['price_change_pct'], yy):
        x = v + 0.8
        if v < r15 < x + 2.8:                    # 라벨이 기준선을 가로지르면 기준선 오른쪽으로 옮긴다
            x = r15 + 0.5
        ax2.text(x, k, f'{v:.1f}%', va='center', fontsize=8.5, color=INK2)
    ax2.set_yticks(yy, p['service'])
    ax2.axvline(r15, color=INK2, linestyle='--', linewidth=1)
    ax2.text(r15, len(p) - 0.35, f'수수료 15% 전액 전가\n({r15:.1f}%)', ha='center', va='bottom', fontsize=8, color=INK2)
    xmax = max(p['price_change_pct'].max() + 6, r15 + 8) if len(p) else 30
    if xmax > r30 - 4:
        ax2.axvline(r30, color=INK2, linestyle=':', linewidth=1)
        ax2.text(r30, len(p) - 0.35, f'수수료 30% 전액 전가\n({r30:.1f}%)', ha='center', va='bottom', fontsize=8, color=INK2)
        xmax = max(xmax, r30 + 6)
    ax2.set_xlim(min(0, p['price_change_pct'].min() - 2) if len(p) else 0, xmax)
    ax2.set_ylim(-0.6, len(p) + 0.9)
    ax2.set_xlabel('안드로이드 인앱 가격 인상률(%)')
    ax2.grid(axis='y', visible=False)
    ax2.set_title(f'(나) 2022년 인앱결제 전환기의 대표 상품 가격 인상률 (n = {len(p)})', loc='left')
    fig.text(0.995, 0.015, '자료: 공개 보도·공식 공지에서 코딩(data/firm_strategy.csv) · 편의표본', ha='right', va='top', fontsize=7.5, color='#8a8983')
    fig.savefig(FIG / 'fig09_strategy_shift.png', bbox_inches='tight')
    plt.close(fig)

    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(ct.to_string())
    print(d[['service', 'pre_android_payment', 'post_android_payment', 'price_change_pct', 'breakeven_fee_pct', 'verification']].to_string())


if __name__ == '__main__':
    main()
