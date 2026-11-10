# -*- coding: utf-8 -*-
"""
15_compare_rerun.py — 처음부터 다시 돌린 결과와 이전에 저장된 결과의 대조

사용: python code/15_compare_rerun.py <이전 outputs 폴더의 사본>
모든 분석 스크립트를 다시 실행한 뒤, outputs/ 의 JSON·CSV 에 든 숫자를 이전 사본과 하나씩 비교한다.
실행 시간처럼 원래 달라지는 값은 뺀다. 출력 outputs/rerun_comparison.csv
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW, OLD = os.path.join(ROOT, 'outputs'), sys.argv[1]
SKIP_KEYS = ('seconds', 'elapsed', 'time')
SKIP_FILES = {'rerun_comparison.csv', 'paper_audit.csv', 'real_verification.csv'}
rows = []


def leaves(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            if any(s in str(k).lower() for s in SKIP_KEYS):
                continue
            yield from leaves(v, f'{path}/{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f'{path}[{i}]')
    elif isinstance(o, bool) or o is None or isinstance(o, str):
        yield path, o
    else:
        yield path, float(o)


for fn in sorted(os.listdir(NEW)):
    if fn in SKIP_FILES or not os.path.exists(os.path.join(OLD, fn)):
        if fn not in SKIP_FILES and fn.endswith(('.json', '.csv')):
            rows.append(dict(file=fn, n_values=0, n_different=0, max_abs_diff=np.nan, max_rel_diff=np.nan, note='이전 사본에 없는 파일'))
        continue
    a, b = os.path.join(OLD, fn), os.path.join(NEW, fn)
    try:
        if fn.endswith('.json'):
            la, lb = dict(leaves(json.load(open(a, encoding='utf-8')))), dict(leaves(json.load(open(b, encoding='utf-8'))))
            keys = sorted(set(la) & set(lb))
            note = '' if set(la) == set(lb) else f'항목 구성이 다름(이전 {len(la)}, 새 {len(lb)})'
            num = [(k, la[k], lb[k]) for k in keys if isinstance(la[k], float) and isinstance(lb[k], float)]
            other = sum(1 for k in keys if not isinstance(la[k], float) and la[k] != lb[k])
        elif fn.endswith('.csv'):
            da, db = pd.read_csv(a), pd.read_csv(b)
            note = '' if da.shape == db.shape and list(da.columns) == list(db.columns) else f'모양이 다름(이전 {da.shape}, 새 {db.shape})'
            num, other = [], 0
            if not note:
                for c in da.columns:
                    if any(s in c.lower() for s in SKIP_KEYS):
                        continue
                    xa, xb = pd.to_numeric(da[c], errors='coerce'), pd.to_numeric(db[c], errors='coerce')
                    if xa.notna().any():
                        num += [(f'{c}[{i}]', float(u), float(v)) for i, (u, v) in enumerate(zip(xa, xb)) if not (np.isnan(u) and np.isnan(v))]
                    else:
                        other += int((da[c].astype(str) != db[c].astype(str)).sum())
        else:
            continue
        if num:
            d = np.array([abs(u - v) if not (np.isnan(u) or np.isnan(v)) else np.inf for _, u, v in num])
            rel = np.array([abs(u - v) / max(abs(u), abs(v), 1e-12) if np.isfinite(dd) else np.inf for (_, u, v), dd in zip(num, d)])
            worst = num[int(np.argmax(d))]
            ndiff = int(((d > 1e-6) & (rel > 1e-6)).sum())
            rows.append(dict(file=fn, n_values=len(num), n_different=ndiff + other, max_abs_diff=float(d.max()), max_rel_diff=float(rel.max()),
                             note=(note + f' 가장 큰 차이: {worst[0]} {worst[1]:.6g} → {worst[2]:.6g}') if d.max() > 1e-6 else note))
        else:
            rows.append(dict(file=fn, n_values=0, n_different=other, max_abs_diff=0.0, max_rel_diff=0.0, note=note))
    except Exception as e:
        rows.append(dict(file=fn, n_values=0, n_different=-1, max_abs_diff=np.nan, max_rel_diff=np.nan, note=f'비교 실패: {e!r}'))
out = pd.DataFrame(rows)
out.to_csv(os.path.join(NEW, 'rerun_comparison.csv'), index=False, encoding='utf-8-sig')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 90); pd.set_option('display.max_rows', 200)
print(out.to_string())
print('파일', len(out), '숫자', int(out.n_values.sum()), '달라진 값', int(out.n_different.clip(lower=0).sum()), '비교 실패', int((out.n_different < 0).sum()))
