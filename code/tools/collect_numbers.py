# -*- coding: utf-8 -*-
"""outputs/*.csv, *.json 을 하나로 모아 논문 생성 스크립트가 읽을 paper_numbers.json 을 만든다."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
O = ROOT / 'outputs'
rec = lambda name, **kw: json.loads(pd.read_csv(O / name, **kw).to_json(orient='records', force_ascii=False))
n = dict(
    flow=rec('sample_flow.csv'), prev=rec('observed_prevalence_by_wave.csv'), calib=rec('calibration_check.csv'),
    sel=rec('model_selection.csv'), inv=rec('measurement_invariance.csv'), tests=rec('transition_homogeneity_tests.csv'),
    prof=rec('response_profiles.csv'), trans=rec('transition_probabilities.csv'), occ=rec('state_occupancy.csv'),
    bvr=rec('bivariate_residuals.csv'), sens=rec('sensitivity.csv'), mc=rec('mc_summary.csv'), mck=rec('mc_kselect_summary.csv'),
    diag=json.load(open(O / 'classification_diagnostics.json')), run=json.load(open(O / 'run_summary.json', encoding='utf-8')),
    py=json.load(open(O / 'python_estimates.json')),
    cross=rec('r_crosscheck.csv') if (O / 'r_crosscheck.csv').exists() else [],
    agg=json.loads(pd.read_csv(ROOT / 'data' / 'kisdi_public_aggregates.csv').to_json(orient='records', force_ascii=False)),
    ret=json.loads(pd.read_csv(ROOT / 'data' / 'kisdi_panel_retention.csv').to_json(orient='records', force_ascii=False)),
)
json.dump(n, open(O / 'paper_numbers.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('paper_numbers.json written:', {k: (len(v) if hasattr(v, '__len__') else v) for k, v in n.items()})
