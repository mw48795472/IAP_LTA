# -*- coding: utf-8 -*-
"""
16_audit_selftest.py — 점검 스크립트(14)가 틀린 값을 실제로 잡아내는지 시험한다

'모두 일치'라는 결과는 점검이 아무것도 보지 않아도 나올 수 있다. 그래서 결과 파일의 사본에 일부러 틀린 값을 하나씩 넣고
점검을 다시 돌려, 해당 항목이 '불일치'로 바뀌는지 확인한다. 원래의 결과 파일은 건드리지 않는다.

출력 outputs/audit_selftest.csv
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'outputs')
DOCX = os.path.join(ROOT, 'paper', '한국_인앱결제_LTA_논문_20261111.docx')


def jedit(folder, name, fn):
    p = os.path.join(folder, name)
    o = json.load(open(p, encoding='utf-8'))
    fn(o)
    json.dump(o, open(p, 'w', encoding='utf-8'), ensure_ascii=False)


def cedit(folder, name, fn):
    p = os.path.join(folder, name)
    d = pd.read_csv(p)
    fn(d)
    d.to_csv(p, index=False, encoding='utf-8-sig')


def m_price(f):
    jedit(f, 'prop1_summary.json', lambda o: o['price_change_pct_raised'].__setitem__('median', o['price_change_pct_raised']['median'] + 0.5))


def m_transition(f):
    def g(o):
        o['main']['A'][1][2][1] += 0.05
    jedit(f, 'real_summary.json', g)


def m_loglik(f):
    jedit(f, 'paper_numbers.json', lambda o: o['py'].__setitem__('loglik_het', o['py']['loglik_het'] + 1.0))


def m_mc(f):
    cedit(f, 'mc_replicates.csv', lambda d: d.__setitem__('lr_p', d['lr_p'].where(d.index >= 30, 0.0)))


def m_prev(f):
    def g(o):
        o['prevalence'][3]['inapp_item'] += 0.3
    jedit(f, 'real_summary.json', g)


def m_covmc(f):
    cedit(f, 'cov_mc_replicates.csv', lambda d: d.__setitem__('wald_p', d['wald_p'].where(d.index >= 20, 0.0)))


def m_persons(f):
    jedit(f, 'real_summary.json', lambda o: o.__setitem__('n_persons', o['n_persons'] + 5))


CASES = [
    ('사업자 자료: 인상률 중위값을 0.5 올림', m_price, 'Ⅳ.8 연구명제', None),
    ('원자료: 전이확률 하나를 0.05 올림', m_transition, 'Ⅴ.5 표 29', None),
    ('모의패널: 로그우도를 1 올림', m_loglik, 'Ⅳ.2~6 모의패널', None),
    ('몬테카를로: 반복 30건의 유의확률을 0으로', m_mc, 'Ⅳ.7 몬테카를로', None),
    ('원자료: 표 24의 한 칸을 0.3 올림', m_prev, 'Ⅴ.1 표 24', None),
    ('공변량 모의: 반복 20건의 유의확률을 0으로', m_covmc, 'Ⅳ.10 공변량(모의)', None),
    ('원자료: 개인 수를 5 늘림', m_persons, 'Ⅴ 원자료', None),
    ('워드 파일: 본문의 11,362를 11,999로 바꿈', None, '완성 파일', ('11,362', '11,999')),
    ('출처 재확인 표: 한 행을 지움', lambda f: cedit(f, 'fact_check.csv', lambda d: d.drop(d.index[-1], inplace=True)), '출처 재확인', None),
    ('워드 파일: 고친 웨이브 시행일을 되돌림', None, '출처 재확인', ('4월 1일 9,000원', '3월 29일 9,000원')),
]


def run(folder, docx=None):
    env = dict(os.environ, AUDIT_OUT=folder, PYTHONIOENCODING='utf-8')
    if docx:
        env['AUDIT_DOCX'] = docx
    subprocess.run([sys.executable, os.path.join(HERE, '14_audit_paper_numbers.py')], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return pd.read_csv(os.path.join(folder, 'paper_audit.csv'))


rows = []
tmp = tempfile.mkdtemp(prefix='audit_selftest_')
try:
    base_dir = os.path.join(tmp, 'base')
    shutil.copytree(OUT, base_dir)
    if os.path.exists(os.path.join(base_dir, 'paper_audit.csv')):
        os.remove(os.path.join(base_dir, 'paper_audit.csv'))
    base = run(base_dir)
    rows.append(dict(case='아무것도 바꾸지 않음', expected_group='(없음)', flagged=int((base.result == '불일치').sum()), flagged_groups='', passed=bool((base.result == '불일치').sum() == 0)))
    for i, (label, mut, group, docx_swap) in enumerate(CASES):
        d = os.path.join(tmp, f'case{i}')
        shutil.copytree(OUT, d)
        if os.path.exists(os.path.join(d, 'paper_audit.csv')):
            os.remove(os.path.join(d, 'paper_audit.csv'))
        docx = None
        if mut:
            mut(d)
        if docx_swap:
            docx = os.path.join(tmp, f'case{i}.docx')
            with zipfile.ZipFile(DOCX) as zin, zipfile.ZipFile(docx, 'w', zipfile.ZIP_DEFLATED) as zout:
                for it in zin.infolist():
                    data = zin.read(it.filename)
                    if it.filename == 'word/document.xml':
                        data = data.decode('utf-8').replace(docx_swap[0], docx_swap[1]).encode('utf-8')
                    zout.writestr(it, data)
        a = run(d, docx)
        bad = a[a.result == '불일치']
        rows.append(dict(case=label, expected_group=group, flagged=int(len(bad)), flagged_groups=', '.join(sorted(set(bad.group))), passed=bool(group in set(bad.group))))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
out = pd.DataFrame(rows)
out.to_csv(os.path.join(OUT, 'audit_selftest.csv'), index=False, encoding='utf-8-sig')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 80)
print(out.to_string())
print('자체 시험 통과' if out.passed.all() else '자체 시험 실패 있음')
