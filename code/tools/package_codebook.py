# -*- coding: utf-8 -*-
"""
package_codebook.py — 코드집 ZIP 만들기

포함: code/, data/(개인 원자료가 있는 data/private 포함), outputs/, figures/, paper/, README.md
제외: 캐시 폴더, 다른 ZIP, 이전 날짜(20261107) 산출물, 임시 파일

주의: data/private 에는 한국미디어패널 개인 원자료(KISDI 미디어통계포털에서 이용 동의 후 내려받은 것)가 들어 있다.
      이 ZIP 을 다른 사람에게 넘기기 전에 내려받을 때 동의한 유의사항이 재배포를 허용하는지 확인할 것.
      원자료를 빼고 묶으려면 --no-private 를 붙인다.

실행: python code/tools/package_codebook.py [YYYYMMDD] [--no-private]
"""
import datetime
import os
import sys
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
args = [a for a in sys.argv[1:] if not a.startswith('--')]
stamp = args[0] if args else datetime.date.today().strftime('%Y%m%d')
no_private = '--no-private' in sys.argv
out = root / f'한국_인앱결제_LTA_코드집_{stamp}{"_원자료제외" if no_private else ""}.zip'
skip_dirs = {'__pycache__', '.ipynb_checkpoints', 'node_modules'} | ({'private'} if no_private else set())
skip_names = {'mc_run_log.txt', 'Rplots.pdf'}

n, n_private, raw_bytes = 0, 0, 0
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if p.is_dir() or any(part in skip_dirs for part in rel.parts) or p.name.startswith('~$'):
            continue
        if p.suffix == '.zip' or '20261107' in p.name or p.name in skip_names:
            continue
        if rel.parts[0] == 'paper' and stamp not in p.name:      # 이전 날짜의 논문·발표자료는 넣지 않는다
            continue
        src = p
        # 논문 워드 파일이 Word에서 열려 있어 제자리에 다시 쓰지 못했을 때, 다른 곳에 만든 최신본을 같은 이름으로 넣는다
        if os.environ.get('PAPER_DOCX_FROM') and rel.parts[0] == 'paper' and p.name == f'한국_인앱결제_LTA_논문_{stamp}.docx':
            src = Path(os.environ['PAPER_DOCX_FROM'])
        z.write(src, f'Korea_InApp_LTA_codebook/{rel.as_posix()}')
        n += 1
        if 'private' in rel.parts:
            n_private += 1
            raw_bytes += p.stat().st_size
with zipfile.ZipFile(out) as z:
    bad = z.testzip()
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
print(out.name, n, 'files', round(out.stat().st_size / 1e6, 1), 'MB', 'zip test:', 'OK' if bad is None else bad)
print('private files included:', n_private, round(raw_bytes / 1e6, 1), 'MB uncompressed')
print(os.fspath(out))
