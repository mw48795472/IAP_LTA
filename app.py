# -*- coding: utf-8 -*-
"""
app.py — 한국 인앱결제 강제금지 규제와 디지털 콘텐츠 소비 상태의 전이: 결과 대시보드

실행:  streamlit run app.py
이 앱은 outputs/ 와 data/ 에 저장된 집계 결과만 읽는다. 개인 원자료(data/private)는 필요하지 않다.
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
OUT, DATA, PAPER = ROOT / 'outputs', ROOT / 'data', ROOT / 'paper'

# 색: 범주 색은 고정 순서로 쓰고(파랑, 주황, 청록, 노랑), 크기는 파랑 한 색의 밝기로 나타낸다
BLUE, ORANGE, AQUA, YELLOW = '#2a78d6', '#eb6834', '#1baf7a', '#eda100'
INK, MUTED, GRID, BAND = '#1f2937', '#6b7280', '#e5e7eb', '#f3f6fa'
SEQ = ['#f4f8fe', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
STATE_COLOR = {'S1 저소비': BLUE, 'S2 구독 중심': ORANGE, 'S3 복합 구매': AQUA}
ITEM_KO = {'paid_app': '유료 앱 구입', 'inapp_item': '앱 내 아이템 구입', 'paid_video': '영상 유료 이용', 'paid_music': '음악 유료 이용'}
ITEM_COLOR = {'paid_app': BLUE, 'inapp_item': ORANGE, 'paid_video': AQUA, 'paid_music': YELLOW}
HIKE_NOTE = '옅은 띠는 2022년 인앱 가격 인상이 걸친 구간(2021→2022, 2022→2023)이다.'

st.set_page_config(page_title='인앱결제 규제와 콘텐츠 소비 전이', page_icon='📊', layout='wide')


@st.cache_data(show_spinner=False)
def csv(name, folder='outputs'):
    p = ROOT / folder / name
    return pd.read_csv(p) if p.exists() else None


@st.cache_data(show_spinner=False)
def js(name):
    p = OUT / name
    return json.load(open(p, encoding='utf-8')) if p.exists() else None


def need(*frames):
    """필요한 결과 파일이 없으면 안내하고 False 를 돌려준다."""
    if any(f is None for f in frames):
        st.info('이 화면에 필요한 결과 파일이 outputs/ 에 없습니다. README의 재현 순서대로 분석을 먼저 실행하세요.')
        return False
    return True


def style(fig, height=380, ytitle=None, xtitle=None, pct=False, legend=True):
    fig.update_layout(
        template='plotly_white', height=height, margin=dict(l=10, r=10, t=30, b=10), font=dict(color=INK, size=13),
        hoverlabel=dict(font_size=13), showlegend=legend,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0, title_text=''),
    )
    fig.update_xaxes(title_text=xtitle, showgrid=False, linecolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(title_text=ytitle, gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED), ticksuffix='%' if pct else '')
    return fig


def show(fig):
    st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})


def table(df, caption='표로 보기', **kw):
    with st.expander(caption):
        st.dataframe(df, width='stretch', hide_index=True, **kw)


def hike_band(fig, x0=0.5, x1=2.5):
    fig.add_vrect(x0=x0, x1=x1, fillcolor=BAND, line_width=0, layer='below')


def line_ci(fig, x, y, lo, hi, name, color, fmt='.1f', suffix='%'):
    """신뢰구간을 오차 막대로 붙인 꺾은선."""
    fig.add_trace(go.Scatter(
        x=x, y=y, name=name, mode='lines+markers', line=dict(color=color, width=2), marker=dict(size=8, line=dict(color='white', width=2)),
        error_y=dict(type='data', symmetric=False, array=[h - v for h, v in zip(hi, y)], arrayminus=[v - l for v, l in zip(y, lo)], color=color, thickness=1.2, width=4),
        customdata=list(zip(lo, hi)), hovertemplate=f'%{{x}}<br>{name}: %{{y:{fmt}}}{suffix} (95% 구간 %{{customdata[0]:{fmt}}}~%{{customdata[1]:{fmt}}})<extra></extra>',
    ))


# ───────────────────────── 자료 읽기 ─────────────────────────
rs = js('real_summary.json')
prev = csv('real_prevalence_by_wave.csv')
occ = csv('real_state_occupancy.csv')
tp = csv('real_transition_probabilities.csv')
prof = csv('real_response_profiles.csv')
man = csv('real_manifest_transitions.csv')
con = csv('real_regime_contrasts.csv')
expo = csv('real_exposure_logit.csv')

st.title('인앱결제 강제금지 규제와 디지털 콘텐츠 소비 상태의 전이')
st.caption('KISDI 한국미디어패널 개인 원자료 2020~2025년의 잠재전이분석(LTA) 결과. 이 화면은 저장된 집계 결과만 보여 주며, 개인 단위 자료는 들어 있지 않다.')

tabs = st.tabs(['요약', '유료 이용 추이', '잠재상태', '전이확률', '가격 인상과 노출', '모의실험', '검증', '논문'])

# ───────────────────────── 1. 요약 ─────────────────────────
with tabs[0]:
    if need(rs, occ, tp):
        c = st.columns(4)
        c[0].metric('분석 대상 개인', f"{rs['n_persons']:,}명")
        c[1].metric('가구', f"{rs['n_households']:,}가구")
        c[2].metric('개인-연도 관측', f"{rs['n_person_waves']:,}건")
        c[3].metric('조사 연도', f"{rs['waves'][0]}~{rs['waves'][-1]}년")

        o = occ.pivot(index='wave', columns='state', values='estimate') * 100
        s3 = tp[(tp.from_state == 'S3 복합 구매')].pivot(index='interval', columns='to_state', values='estimate')
        stay = ' → '.join(f'{v:.2f}' for v in s3['S3 복합 구매'])
        lines = [
            f"**세 가지 소비 상태.** 저소비 {o['S1 저소비'].iloc[0]:.1f}% → {o['S1 저소비'].iloc[-1]:.1f}%, 구독 중심 {o['S2 구독 중심'].iloc[0]:.1f}% → {o['S2 구독 중심'].iloc[-1]:.1f}%, "
            f"복합 구매 {o['S3 복합 구매'].iloc[0]:.1f}% → {o['S3 복합 구매'].iloc[-1]:.1f}% ({rs['waves'][0]}년 → {rs['waves'][-1]}년).",
            f"**복합 구매 상태의 유지확률**은 구간별로 {stay} 이었다. 2021→2023년에 이탈이 몰렸다.",
        ]
        if con is not None:
            k = con[(con.transition == '복합 구매 → 구독 중심') & (con.contrast == '가격 인상기 − 이전')].iloc[0]
            lines.append(f"**가격 인상기의 변화.** 복합 구매 → 구독 중심 이동확률이 이전 구간보다 {k.estimate:+.3f} 높았다(가구 부트스트랩 95% 구간 {k.lo:.3f}~{k.hi:.3f}).")
        if expo is not None:
            e = expo[(expo.outcome == '앱 내 아이템 구입') & (expo.kind == '지속(구입자)') & (expo['index'] == '주 지수') & (expo.term == '노출 × 가격 인상기')].iloc[0]
            lines.append(f"**그러나 가격 인상의 효과로 볼 수는 없다.** 값이 오른 영상·음원의 유료 이용은 줄지 않았고, 개인별 가격 인상 노출 지수는 이탈을 예측하지 못했다"
                         f"(노출 × 가격 인상기 {e.estimate:.3f}, p = {e.p:.2f}). 2021년은 코로나 시기의 고점이었고 2024년에는 조사 측정이 달라진 흔적이 있다.")
        for t in lines:
            st.markdown('- ' + t)

        st.subheader('소비 상태의 비중')
        fig = go.Figure()
        for s, col in STATE_COLOR.items():
            d = occ[occ.state == s]
            line_ci(fig, d.wave.astype(str), d.estimate * 100, d.lo * 100, d.hi * 100, s, col)
        show(style(fig, ytitle='응답자 비중', pct=True))
        table(occ.assign(estimate=occ.estimate * 100, lo=occ.lo * 100, hi=occ.hi * 100).round(1).rename(columns={'wave': '연도', 'state': '상태', 'estimate': '비중(%)', 'lo': '하한', 'hi': '상한'}))

    ev = csv('policy_events.csv', 'data')
    if ev is not None:
        st.subheader('정책·사건 연표')
        lane_color = {'한국: 입법·집행': BLUE, '플랫폼 대응': ORANGE, '해외 동향': AQUA}
        fig = go.Figure()
        for lane, col in lane_color.items():
            d = ev[ev.lane == lane]
            fig.add_trace(go.Scatter(x=pd.to_datetime(d.date), y=[lane] * len(d), mode='markers', name=lane, marker=dict(size=13, color=col, line=dict(color='white', width=2)),
                                     customdata=d[['label', 'date']], hovertemplate='%{customdata[1]}<br>%{customdata[0]}<extra></extra>'))
        fig = style(fig, height=230, legend=False)
        fig.update_yaxes(showgrid=False, tickfont=dict(color=INK))
        fig.update_xaxes(showgrid=True, gridcolor=GRID)
        show(fig)
        table(ev.sort_values('date').rename(columns={'date': '날짜', 'lane': '구분', 'label': '내용', 'source': '출처', 'url': '링크'}), '연표를 표로 보기(출처 포함)',
              column_config={'링크': st.column_config.LinkColumn('링크', display_text='열기')})

    pdfs = sorted(PAPER.glob('*.pdf')) if PAPER.exists() else []
    if pdfs:
        st.caption('논문 전문은 맨 오른쪽의 "논문" 탭에서 바로 읽거나 내려받을 수 있다.')

# ───────────────────────── 2. 유료 이용 추이 ─────────────────────────
with tabs[1]:
    if need(prev, man):
        st.subheader('연도별 유료 이용 비율')
        st.caption('전체 응답자 대비 가중 비율. 영상 유료 이용은 2020년에 해당 문항이 없다. 2024년에는 영상 문항의 수준이 한 번에 달라져 측정 단절로 처리하였다.')
        fig = go.Figure()
        for it, col in ITEM_COLOR.items():
            fig.add_trace(go.Scatter(x=prev.wave.astype(str), y=prev[it], name=ITEM_KO[it], mode='lines+markers', line=dict(color=col, width=2),
                                     marker=dict(size=8, line=dict(color='white', width=2)), hovertemplate='%{x}년<br>' + ITEM_KO[it] + ': %{y:.1f}%<extra></extra>'))
        show(style(fig, ytitle='응답자 대비 비율', pct=True))
        table(prev[['wave', 'respondents'] + list(ITEM_KO)].rename(columns={'wave': '연도', 'respondents': '응답자 수', **ITEM_KO}).round(2))

        st.subheader('이듬해에도 이어졌는가: 지속률과 진입률')
        kind = st.radio('보기', ['지속률(올해 구입자 중 이듬해에도 구입)', '진입률(올해 비구입자 중 이듬해 구입)'], horizontal=True, label_visibility='collapsed')
        key = 'persist' if kind.startswith('지속') else 'entry'
        order = list(dict.fromkeys(man.interval))
        fig = go.Figure()
        for it, col in ITEM_COLOR.items():
            d = man[man.item == it]
            line_ci(fig, d.interval, d[key] * 100, d[key + '_lo'] * 100, d[key + '_hi'] * 100, ITEM_KO[it], col)
        fig.update_xaxes(categoryorder='array', categoryarray=order)
        hike_band(fig)
        show(style(fig, ytitle=kind.split('(')[0], pct=True))
        st.caption(HIKE_NOTE + ' 모형을 거치지 않고 두 해 자료를 직접 이어 계산한 값이다.')
        m2 = man.assign(item=man.item.map(ITEM_KO))
        for k in ('persist', 'persist_lo', 'persist_hi', 'entry', 'entry_lo', 'entry_hi'):
            m2[k] = (m2[k] * 100).round(1)
        table(m2.rename(columns={'item': '지표', 'interval': '구간', 'n': '두 해 모두 응답', 'n_buyers': '올해 구입자', 'persist': '지속률(%)', 'persist_lo': '지속 하한', 'persist_hi': '지속 상한',
                                 'entry': '진입률(%)', 'entry_lo': '진입 하한', 'entry_hi': '진입 상한'}))

    flow = csv('real_sample_flow.csv')
    if flow is not None:
        st.subheader('패널 유지')
        table(flow.rename(columns={'wave': '연도', 'respondents': '응답자', 'retained_from_prev': '전년도에서 유지', 'retention_pct': '유지율(%)', 'new_or_returning': '신규·복귀'}), '연도별 응답자와 유지율')

# ───────────────────────── 3. 잠재상태 ─────────────────────────
with tabs[2]:
    if need(prof, occ):
        st.subheader('상태별 응답확률: 각 상태는 어떤 소비인가')
        st.caption('각 상태에 속한 사람이 해당 항목을 유료로 이용할 확률. 영상 문항은 2024년부터 응답확률을 따로 추정하였다(부분 측정불변).')
        p = prof.assign(label=prof.item_ko + prof.period.map(lambda s: '' if s == '전 기간' else f'<br>({s})'))
        fig = go.Figure()
        for s, col in STATE_COLOR.items():
            d = p[p.state == s]
            fig.add_trace(go.Bar(x=d.label, y=d.estimate * 100, name=s, marker=dict(color=col, line=dict(color='white', width=2), cornerradius=4),
                                 error_y=dict(type='data', symmetric=False, array=(d.hi - d.estimate) * 100, arrayminus=(d.estimate - d.lo) * 100, color=MUTED, thickness=1.2, width=3),
                                 hovertemplate='%{x}<br>' + s + ': %{y:.1f}%<extra></extra>'))
        fig.update_layout(barmode='group', bargap=0.25, bargroupgap=0.06)
        show(style(fig, ytitle='유료 이용 확률', pct=True, height=400))
        table(prof.assign(estimate=prof.estimate * 100, lo=prof.lo * 100, hi=prof.hi * 100).round(1).drop(columns='item').rename(
            columns={'item_ko': '지표', 'state': '상태', 'period': '기간', 'estimate': '확률(%)', 'lo': '하한', 'hi': '상한'}))

    ms = csv('real_model_selection.csv')
    if ms is not None:
        st.subheader('상태 수의 선택')
        st.caption('BIC가 낮을수록 좋다. 상태 수를 늘릴 때의 개선 폭과 가장 작은 상태의 비중을 함께 보고 세 상태를 택하였다.')
        fig = go.Figure()
        for meas, col in zip(ms.measurement.unique(), (BLUE, ORANGE)):
            d = ms[ms.measurement == meas]
            fig.add_trace(go.Scatter(x=d.K, y=d.bic, name=meas, mode='lines+markers', line=dict(color=col, width=2), marker=dict(size=8, line=dict(color='white', width=2)),
                                     hovertemplate='상태 수 %{x}<br>' + meas + ' BIC: %{y:,.0f}<extra></extra>'))
        fig = style(fig, ytitle='BIC', xtitle='상태 수(K)', height=340)
        fig.update_xaxes(dtick=1)
        show(fig)
        table(ms.rename(columns={'measurement': '측정 모형', 'loglik': '로그우도', 'npar': '모수 수', 'bic': 'BIC', 'aic': 'AIC', 'min_state_share': '가장 작은 상태 비중',
                                 'n_replicated': '같은 해에 도달한 시작값 수', 'n_starts': '시작값 수', 'converged': '수렴'}).round(3))

    sens = csv('real_sensitivity.csv')
    if sens is not None:
        st.subheader('민감도 분석')
        st.caption('가중 여부, 측정 모형, 표본 범위를 바꾸어도 복합 구매 상태의 비중과 유지확률의 흐름이 유지되는지 본 것이다.')
        st.dataframe(sens.round(3), width='stretch', hide_index=True)

# ───────────────────────── 4. 전이확률 ─────────────────────────
with tabs[3]:
    if need(tp):
        states = list(STATE_COLOR)
        intervals = list(dict.fromkeys(tp.interval))
        st.subheader('구간별 전이행렬')
        iv = st.radio('구간', intervals, horizontal=True, index=1)
        d = tp[tp.interval == iv]
        z = d.pivot(index='from_state', columns='to_state', values='estimate').loc[states, states]
        lo = d.pivot(index='from_state', columns='to_state', values='lo').loc[states, states]
        hi = d.pivot(index='from_state', columns='to_state', values='hi').loc[states, states]
        left, right = st.columns([1, 1.25])
        with left:
            fig = go.Figure(go.Heatmap(
                z=z.values, x=states, y=states, zmin=0, zmax=1, colorscale=[[i / (len(SEQ) - 1), c] for i, c in enumerate(SEQ)], xgap=2, ygap=2,
                text=z.values, texttemplate='%{text:.2f}', textfont=dict(size=15), customdata=[[f'{a:.2f}~{b:.2f}' for a, b in zip(r1, r2)] for r1, r2 in zip(lo.values, hi.values)],
                hovertemplate='올해 %{y} → 이듬해 %{x}<br>확률 %{z:.3f} (95% 구간 %{customdata})<extra></extra>', colorbar=dict(title='확률', thickness=12, len=0.8)))
            fig = style(fig, height=380, xtitle='이듬해 상태', ytitle='올해 상태', legend=False)
            fig.update_yaxes(autorange='reversed', showgrid=False, tickfont=dict(color=INK))
            fig.update_xaxes(side='bottom', tickfont=dict(color=INK))
            show(fig)
        with right:
            origin = st.selectbox('출발 상태를 골라 구간별 흐름 보기', states, index=2)
            fig = go.Figure()
            for s, col in STATE_COLOR.items():
                q = tp[(tp.from_state == origin) & (tp.to_state == s)]
                name = f'{s}에 머무름' if s == origin else f'→ {s}'
                line_ci(fig, q.interval, q.estimate, q.lo, q.hi, name, col, fmt='.2f', suffix='')
            fig.update_xaxes(categoryorder='array', categoryarray=intervals)
            hike_band(fig)
            fig = style(fig, height=330, ytitle='전이확률')
            fig.update_yaxes(range=[0, 1.02])
            show(fig)
            st.caption(HIKE_NOTE + ' 막대는 가구 단위 부트스트랩 95% 구간.')
        table(tp.round(3).rename(columns={'interval': '구간', 'from_state': '올해 상태', 'to_state': '이듬해 상태', 'estimate': '확률', 'lo': '하한', 'hi': '상한'}), '전이확률 전체를 표로 보기')

    if con is not None:
        st.subheader('가격 인상기와 그 전후의 차이')
        st.caption('가격 인상기(2021→2023년 두 구간 평균)의 전이확률에서 이전(2020→2021년) 또는 이후(2023→2025년)의 값을 뺀 것. 구간이 0을 포함하지 않으면 차이가 뚜렷하다는 뜻이다.')
        which = st.radio('비교', list(con.contrast.unique()), horizontal=True, label_visibility='collapsed')
        d = con[con.contrast == which].iloc[::-1]
        clear = (d.lo > 0) | (d.hi < 0)
        fig = go.Figure(go.Scatter(
            x=d.estimate, y=d.transition, mode='markers', marker=dict(size=11, color=[BLUE if c else '#9ca3af' for c in clear], line=dict(color='white', width=2)),
            error_x=dict(type='data', symmetric=False, array=d.hi - d.estimate, arrayminus=d.estimate - d.lo, color=MUTED, thickness=1.5, width=5),
            customdata=list(zip(d.lo, d.hi)), hovertemplate='%{y}<br>차이 %{x:+.3f} (95% 구간 %{customdata[0]:+.3f}~%{customdata[1]:+.3f})<extra></extra>'))
        fig.add_vline(x=0, line_color=MUTED, line_width=1)
        fig = style(fig, height=330, xtitle='전이확률의 차이', legend=False)
        fig.update_yaxes(showgrid=False, tickfont=dict(color=INK))
        fig.update_xaxes(showgrid=True, gridcolor=GRID)
        show(fig)
        st.caption('파란 점은 95% 구간이 0을 포함하지 않는 항목, 회색 점은 포함하는 항목.')
        table(con.round(3).rename(columns={'transition': '전이', 'contrast': '비교', 'estimate': '차이', 'lo': '하한', 'hi': '상한', 'boot_share_positive': '부트스트랩에서 양수인 비율'}))

# ───────────────────────── 5. 가격 인상과 노출 ─────────────────────────
with tabs[4]:
    svc = csv('prop1_service_types.csv')
    if need(svc):
        st.subheader('2022년 안드로이드 인앱 가격 인상률')
        pr = svc.dropna(subset=['price_change_pct']).sort_values('price_change_pct')
        y2022 = pr.android_price_change_date.astype(str).str.startswith('2022')
        full = 100 * 0.15 / 0.85
        fig = go.Figure(go.Bar(
            x=pr.price_change_pct, y=pr.service, orientation='h', marker=dict(color=[ORANGE if v else '#c5cad3' for v in y2022], cornerradius=4),
            text=[f'{v:.1f}%' for v in pr.price_change_pct], textposition='outside', textfont=dict(color=INK), cliponaxis=False,
            customdata=pr[['android_price_old_krw', 'android_price_new_krw', 'android_price_change_date', 'price_product']],
            hovertemplate='%{y}<br>%{customdata[3]}<br>%{customdata[0]:,.0f}원 → %{customdata[1]:,.0f}원 (%{customdata[2]})<br>인상률 %{x:.1f}%<extra></extra>'))
        fig.add_vline(x=full, line_dash='dot', line_color=MUTED, line_width=1.5, layer='below', annotation_text=f'수수료 15% 전액 전가 {full:.1f}%', annotation_position='top', annotation_font_color=MUTED)
        fig = style(fig, height=420, xtitle='인상률', legend=False)
        fig.update_xaxes(ticksuffix='%', showgrid=True, gridcolor=GRID, range=[0, pr.price_change_pct.max() + 7])
        fig.update_yaxes(showgrid=False, tickfont=dict(color=INK))
        show(fig)
        st.caption('주황은 2022년에 값이 바뀐 서비스, 회색은 그 밖의 시기(유튜브 프리미엄 2023년 12월). 보도와 공식 공지에서 코딩한 편의표본이며, FLO는 인상 후 가격 보도가 엇갈린다(9,000원·9,900원).')
        cols = ['service', 'sector', 'pre_type', 'post_type', 'android_price_old_krw', 'android_price_new_krw', 'android_price_change_date', 'price_change_pct', 'web_price_kept']
        table(svc[cols].round(1).rename(columns={'service': '서비스', 'sector': '분야', 'pre_type': '규제 전 결제 방식', 'post_type': '규제 후 대응', 'android_price_old_krw': '종전 가격(원)',
                                                 'android_price_new_krw': '인상 후(원)', 'android_price_change_date': '변경일', 'price_change_pct': '인상률(%)', 'web_price_kept': '웹 가격 유지'}),
              '서비스별 결제 방식과 가격을 표로 보기')

    ct = csv('prop1_crosstab.csv')
    if ct is not None:
        st.subheader('규제 전 결제 방식 × 규제 후 대응')
        st.dataframe(ct.rename(columns={'pre_type': '규제 전 결제 방식'}), width='stretch', hide_index=True)

    if expo is not None:
        st.subheader('가격 인상에 더 많이 노출된 사람이 더 많이 이탈했는가')
        st.caption('개인별 가격 인상 노출 지수(값이 오른 분야를 얼마나 이용했는가)로 이듬해 구입 지속·진입을 예측한 로지스틱 회귀. 표준오차는 가구 군집을 반영하였다. '
                   '"노출 × 가격 인상기"가 0과 구별되지 않으면, 더 많이 노출된 사람이 가격 인상기에 더 많이 이탈했다는 증거가 없다는 뜻이다.')
        a, b, c3 = st.columns(3)
        oc = a.selectbox('결과 변수', list(expo.outcome.unique()))
        kd = b.selectbox('종류', list(expo.kind.unique()))
        ix = c3.selectbox('노출 지수', list(expo['index'].unique()))
        d = expo[(expo.outcome == oc) & (expo.kind == kd) & (expo['index'] == ix)].iloc[::-1]
        lo, hi = d.estimate - 1.96 * d.se, d.estimate + 1.96 * d.se
        clear = (lo > 0) | (hi < 0)
        fig = go.Figure(go.Scatter(
            x=d.estimate, y=d.term, mode='markers', marker=dict(size=11, color=[BLUE if v else '#9ca3af' for v in clear], line=dict(color='white', width=2)),
            error_x=dict(type='data', array=1.96 * d.se, color=MUTED, thickness=1.5, width=5), customdata=list(zip(d.se, d.p)),
            hovertemplate='%{y}<br>계수 %{x:.3f} (표준오차 %{customdata[0]:.3f}, p = %{customdata[1]:.3f})<extra></extra>'))
        fig.add_vline(x=0, line_color=MUTED, line_width=1)
        fig = style(fig, height=300, xtitle='로짓 계수(95% 구간)', legend=False)
        fig.update_yaxes(showgrid=False, tickfont=dict(color=INK))
        fig.update_xaxes(showgrid=True, gridcolor=GRID)
        show(fig)
        if len(d):
            st.caption(f"관측 {int(d.n.iloc[0]):,}건, 개인 {int(d.n_persons.iloc[0]):,}명, 가구 {int(d.n_households.iloc[0]):,}가구. 파란 점은 95% 구간이 0을 포함하지 않는 항.")
        table(d.iloc[::-1][['term', 'estimate', 'se', 'z', 'p']].round(3).rename(columns={'term': '항', 'estimate': '계수', 'se': '표준오차'}))

# ───────────────────────── 6. 모의실험 ─────────────────────────
with tabs[5]:
    mc = csv('mc_summary.csv')
    if need(mc):
        st.subheader('이 방법은 전이확률의 변화를 얼마나 잘 잡아내는가(검정력)')
        st.caption('원자료를 얻기 전에 공표 표본 크기와 유지율에 맞춘 모의패널로 한 실험. 심어 둔 변화의 크기와 표본 크기에 따라 "변화 없음" 가설을 기각한 비율이다.')
        fig = go.Figure()
        for n, col in zip(sorted(mc.N.unique()), (BLUE, ORANGE, AQUA)):
            d = mc[mc.N == n].sort_values('delta')
            fig.add_trace(go.Scatter(x=d.delta, y=d.reject_rate_regime * 100, name=f'N = {n:,}', mode='lines+markers', line=dict(color=col, width=2), marker=dict(size=8, line=dict(color='white', width=2)),
                                     customdata=d.reps, hovertemplate='변화 크기 %{x:.2f}<br>' + f'N = {n:,}' + ': 기각률 %{y:.1f}% (반복 %{customdata}회)<extra></extra>'))
        fig.add_hline(y=5, line_dash='dot', line_color=MUTED, line_width=1, annotation_text='유의수준 5%', annotation_font_color=MUTED)
        fig = style(fig, ytitle='기각률', xtitle='심어 둔 전이확률 변화의 크기', pct=True, height=360)
        fig.update_xaxes(tickvals=sorted(mc.delta.unique()))
        show(fig)
        table(mc[['N', 'delta', 'reps', 'reject_rate', 'reject_rate_regime', 'pct_converged']].round(3).rename(
            columns={'delta': '변화 크기', 'reps': '반복', 'reject_rate': '기각률(전체 검정)', 'reject_rate_regime': '기각률(국면 검정)', 'pct_converged': '수렴(%)'}))

    cmc = csv('cov_mc_summary.csv')
    if cmc is not None:
        st.subheader('공변량(가격 인상 노출 지수) 모형의 모의실험')
        st.caption('노출 지수와 가격 인상기의 상호작용을 심은 경우(효과 있음)와 심지 않은 경우의 기각률.')
        st.dataframe(cmc.assign(alt=cmc.alt.map({True: '효과 있음', False: '효과 없음'})).round(3).rename(
            columns={'alt': '설계', 'reps': '반복', 'lr_reject': '기각률(우도비)', 'wald_reject': '기각률(왈드)', 'wald_mean': '추정값 평균', 'wald_sd': '추정값 표준편차',
                     'wald_se_mean': '표준오차 평균', 'pct_converged': '수렴(%)'}), width='stretch', hide_index=True)

# ───────────────────────── 7. 검증 ─────────────────────────
with tabs[6]:
    audit, rerun, fact, self_, ver = csv('paper_audit.csv'), csv('rerun_comparison.csv'), csv('fact_check.csv'), csv('audit_selftest.csv'), csv('real_verification.csv')
    c = st.columns(4)
    if audit is not None:
        c[0].metric('논문 수치 전수 점검', f"{int((audit.result == '일치').sum())} / {len(audit)} 일치")
    if rerun is not None:
        c[1].metric('재실행 대조한 숫자', f"{int(rerun.n_values.sum()):,}개", f"달라진 값 {int(rerun.n_different.clip(lower=0).sum()):,}개", delta_color='off')
    if fact is not None:
        vc = fact.status.value_counts()
        c[2].metric('출처 재확인', f"{int(vc.get('확인', 0))} / {len(fact)} 확인", f"불일치 {int(vc.get('불일치', 0))}, 확인 불가 {int(vc.get('확인 불가', 0))}", delta_color='off')
    if self_ is not None:
        c[3].metric('점검 자체 시험', f"{int(self_.passed.sum())} / {len(self_)} 통과")

    if rerun is not None:
        st.subheader('전체 재실행 대조')
        st.caption('모든 분석을 처음부터 다시 실행해 이전 저장값과 숫자 하나씩 비교한 결과. 달라진 값은 공변량 모의 분석에서만 나왔고(소수 4~5째 자리), 저장값이 추정 엔진을 고치기 전의 것이었기 때문이다. '
                   '재실행값으로 바꾼 뒤 한 번 더 돌렸을 때는 완전히 같았다.')
        only = st.checkbox('달라진 파일만 보기', value=False)
        d = rerun[rerun.n_different != 0] if only else rerun
        st.dataframe(d.rename(columns={'file': '파일', 'n_values': '숫자 수', 'n_different': '달라진 값', 'max_abs_diff': '최대 절대 차이', 'max_rel_diff': '최대 상대 차이', 'note': '비고'}),
                     width='stretch', hide_index=True)
    if fact is not None:
        st.subheader('출처 재확인')
        st.caption('본문에 직접 적은 날짜·금액·가격을 출처 페이지에서 다시 대조한 결과. 불일치와 확인 불가 항목은 논문에서 고치거나 뺐다.')
        pick = st.multiselect('상태', list(fact.status.unique()), default=list(fact.status.unique()))
        st.dataframe(fact[fact.status.isin(pick)][['id', 'claim', 'status', 'source_url', 'note']].rename(columns={'claim': '사실', 'status': '상태', 'source_url': '출처', 'note': '비고'}),
                     width='stretch', hide_index=True, column_config={'출처': st.column_config.LinkColumn('출처', display_text='열기')})
    if audit is not None:
        st.subheader('논문 수치 전수 점검')
        g = st.selectbox('영역', ['전체'] + list(audit.group.unique()))
        d = audit if g == '전체' else audit[audit.group == g]
        st.dataframe(d.rename(columns={'group': '영역', 'item': '점검 항목', 'paper': '논문의 값', 'recomputed': '다시 계산한 값', 'result': '결과', 'note': '비고'}), width='stretch', hide_index=True)
    if ver is not None:
        st.subheader('원자료 결과의 재검증')
        st.dataframe(ver.rename(columns={'group': '영역', 'check': '검사', 'result': '결과', 'detail': '내용'}), width='stretch', hide_index=True)
    if self_ is not None:
        st.subheader('점검 자체 시험')
        st.caption('결과 파일과 워드 파일의 사본에 일부러 틀린 값을 넣었을 때 점검이 그것을 잡아내는지 본 것.')
        st.dataframe(self_.rename(columns={'case': '넣은 오류', 'expected_group': '잡혀야 할 영역', 'flagged': '불일치로 잡힌 수', 'flagged_groups': '잡힌 영역', 'passed': '통과'}),
                     width='stretch', hide_index=True)

# ───────────────────────── 8. 논문 ─────────────────────────
with tabs[7]:
    pdfs = sorted(PAPER.glob('*.pdf')) if PAPER.exists() else []
    if not pdfs:
        st.info('paper/ 폴더에 논문 PDF가 없습니다.')
    else:
        pdf = pdfs[-1]
        st.subheader('논문 전문')
        st.caption('한국 인앱결제 강제금지 규제와 디지털 콘텐츠 소비 상태의 전이: 한국미디어패널 2020~2025년의 잠재전이분석. '
                   '아래에서 바로 읽을 수 있고, 내려받아 볼 수도 있다.')
        a, b = st.columns([1, 3])
        a.download_button('PDF 내려받기', pdf.read_bytes(), file_name=pdf.name, mime='application/pdf', type='primary')
        b.caption(f'파일: {pdf.name} · {pdf.stat().st_size / 1e6:.1f} MB')
        try:
            st.pdf(str(pdf), height=900)
        except Exception:
            # streamlit[pdf] 가 설치되지 않은 환경에서는 화면 안 보기를 건너뛴다
            st.info('이 환경에서는 화면 안에서 PDF를 열 수 없습니다. 위의 버튼으로 내려받아 보세요. (pip install "streamlit[pdf]" 를 설치하면 화면 안에서 열립니다.)')

st.divider()
st.caption('자료: KISDI 한국미디어패널(2020~2025), 공식 문서와 보도. 시기에 따른 전이의 차이를 규제의 인과효과로 읽을 수는 없다. 코드와 논문은 저장소의 README 참조.')
