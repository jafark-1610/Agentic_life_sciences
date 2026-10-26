"""Data-derived numerical grading; isolated execution is a separate required check."""
import os
import sys
sys.dont_write_bytecode = True
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import argparse
import json
import re
from pathlib import Path
import numpy as np
from scipy.special import expit
from model import load_data, read_json, features, slope, occupancy, utility, evidence

HERE = Path(__file__).resolve().parent


def load_answer(path):
    findings = []
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out: findings.append('duplicate key; last value used')
            out[k] = v
        return out
    try:
        return json.loads(Path(path).read_text(), object_pairs_hook=pairs), findings, None
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        return None, findings, 'unreadable JSON: '+type(exc).__name__


def coerce(raw, shape, findings):
    def scan(x):
        if isinstance(x, bool): raise ValueError('boolean is not a number')
        if isinstance(x, str): findings.append('numeric string')
        if isinstance(x, list):
            for v in x: scan(v)
    try:
        scan(raw)
        with np.errstate(all='ignore'):
            a = np.asarray(raw, dtype=float)
        if a.shape == shape: return a
        if len(shape) == 2 and a.shape == tuple(reversed(shape)):
            findings.append('transposed matrix'); return a.T
        if len(shape) == 2 and a.ndim == 1 and a.size == int(np.prod(shape)):
            findings.append('flattened matrix'); return a.reshape(shape)
    except (TypeError, ValueError, OverflowError, RecursionError):
        pass
    return None


def true_outputs(D, truth):
    X = features(D['bits'])
    result = {}
    for p in D['meta']['proteins']:
        en = X@np.asarray(truth['proteins'][p['id']]['coefficients']).T
        apo = expit(-en[:, 0])
        pa = occupancy(en, slope(D['bits'], p), D['meta']['challenge_conditions'])[0]
        util = utility(apo, pa, D['bits'], D['meta'])
        result[p['id']] = dict(energy=en, apo=apo, pa=pa, utility=util)
    return result


def assess(answer, D, analysis_text='', truth=None, load_findings=None):
    contract = read_json(Path(D['data_dir'])/'grading_contract.json') if 'data_dir' in D else None
    if contract is None:
        contract = read_json(HERE.parent/'task/data/grading_contract.json')
    meta = D['meta']; findings = list(load_findings or [])
    result = dict(case_id=meta['case_id'], role='numerical_artifact_grading',
                  pipeline_execution='not established by artifact grading; verify_submission.py required',
                  scientific_gates=[], credit_items=[], report_findings=[], presentation_findings=findings)
    if isinstance(answer, list) and len(answer) == 1 and isinstance(answer[0], dict):
        answer = answer[0]; findings.append('one-object wrapper')
    if not isinstance(answer, dict):
        result.update(final_score=0, passed=False, automatic_zero='answer is not a readable object')
        return result
    if answer.get('schema') != 'thermodynamic_design/1' or answer.get('case_id') != meta['case_id']:
        findings.append('schema or case_id')
    if set(answer)-{'schema', 'case_id', 'calibration', 'proteins'}: findings.append('extra top-level metadata')
    truth = truth or read_json(HERE/'private/truth.json')
    truth_arrays = true_outputs(D, truth)

    def keyed(raw, allowed, fields):
        out = {}
        if not isinstance(raw, list): return out
        for obj in raw:
            if not isinstance(obj, dict) or not isinstance(obj.get('id'), str): continue
            key = obj['id']
            if key not in allowed: findings.append('unknown object id'); continue
            if key in out: findings.append('repeated id; first used'); continue
            if set(obj)-set(fields): findings.append('extra object metadata')
            out[key] = obj
        return out

    def gate(pid, metric, passed, value=None, threshold=None):
        result['scientific_gates'].append(dict(protein=pid, metric=metric, passed=bool(passed),
                                               value=float(value) if value is not None and np.isfinite(value) else None,
                                               threshold=threshold))
    cal = keyed(answer.get('calibration'), {c['id'] for c in meta['screen_conditions']}, ['id', 'background', 'ceiling'])
    cal_normalized = []
    for c in meta['screen_conditions']:
        obj = cal.get(c['id'], {})
        a = coerce([obj.get('background'), obj.get('ceiling')], (2,), findings)
        valid = a is not None and np.isfinite(a).all() and 0 <= a[0] < a[1] <= 1
        gate(c['id'], 'calibration_validity', valid)
        if valid: cal_normalized.append(dict(id=c['id'], background=float(a[0]), ceiling=float(a[1])))
    by_id = keyed(answer.get('proteins'), {p['id'] for p in meta['proteins']},
                  ['id', 'energy', 'apo_folded', 'challenge_a', 'selected_variant'])
    nf, nc, np_ = meta['n_variants'], len(meta['challenge_conditions']), len(meta['proteins'])
    variant_index = {r['variant_id']: i for i, r in enumerate(D['rows'])}
    normalized, raw = [], 0.
    for p in meta['proteins']:
        pid = p['id']; obj = by_id.get(pid, {}); truth_p = truth_arrays[pid]
        en = coerce(obj.get('energy'), (nf, 3), findings)
        apo = coerce(obj.get('apo_folded'), (nf,), findings)
        pa = coerce(obj.get('challenge_a'), (nf, nc), findings)
        selected = obj.get('selected_variant')
        valid = (en is not None and apo is not None and pa is not None and
                 all(np.isfinite(a).all() for a in [en, apo, pa]) and
                 np.min(apo) >= 0 and np.max(apo) <= 1 and np.min(pa) >= 0 and np.max(pa) <= 1 and
                 isinstance(selected, str) and selected in variant_index)
        gate(pid, 'validity', valid)
        metrics = {}
        if valid:
            with np.errstate(over='ignore', invalid='ignore'):
                metrics = dict(energy_rmse=float(np.sqrt(np.mean((en-truth_p['energy'])**2))),
                               energy_p95=float(np.percentile(np.abs(en-truth_p['energy']), 95)),
                               apo_rmse=float(np.sqrt(np.mean((apo-truth_p['apo'])**2))),
                               challenge_rmse=float(np.sqrt(np.mean((pa-truth_p['pa'])**2))),
                               challenge_max_abs=float(np.max(np.abs(pa-truth_p['pa']))),
                               design_regret=float(np.max(truth_p['utility'])-truth_p['utility'][variant_index[selected]]))
            normalized.append(dict(id=pid, energy=en.tolist(), apo_folded=apo.tolist(), challenge_a=pa.tolist(), selected_variant=selected))
        for group in contract['groups']:
            metric, threshold = group['metric'], meta['acceptance_thresholds'][group['threshold']]
            value = metrics.get(metric, np.inf)
            ok = valid and np.isfinite(value) and value <= threshold
            gate(pid, metric, ok, value, threshold)
            points = group['points']/np_ if ok else 0.
            raw += points
            result['credit_items'].append(dict(protein=pid, metric=metric, points=points, maximum=group['points']/np_))
    # Report evidence is independently recomputed from normalized submitted arrays.
    report_ok = False
    try:
        blocks = re.findall(r'```json\s*([\s\S]*?)```', analysis_text)
        assert len(blocks) == 1
        report = json.loads(blocks[0])
        rows = report['proteins']; assert isinstance(rows, list) and len(rows) == np_
        rb = {r['id']: r for r in rows}; assert len(rb) == np_
        assert len(normalized) == np_ and len(cal_normalized) == len(meta['screen_conditions'])
        ev = evidence(dict(proteins=normalized, calibration=cal_normalized), D)
        for r in ev:
            for key, tol in meta['report_tolerances'].items():
                v = rb[r['id']][key]
                assert not isinstance(v, bool) and np.isfinite(float(v)) and abs(float(v)-r[key]) <= tol, r['id']+':'+key
        report_ok = True
    except (ValueError, TypeError, KeyError, AssertionError, OverflowError, IndexError, ZeroDivisionError) as exc:
        result['report_findings'].append('calculated evidence missing, unreadable, or inconsistent: '+str(exc)[:200])
    if report_ok: raw += contract['report_points']
    failed = [g for g in result['scientific_gates'] if not g['passed']]
    capped = min(raw, contract['scientific_gate_cap']) if failed else raw
    final = max(0, capped-(contract['presentation_deduction'] if findings else 0))
    result.update(raw_score=round(raw, 6), scientific_cap_applied=bool(failed),
                  failed_gates=[g['protein']+':'+g['metric'] for g in failed], report_points=5 if report_ok else 0,
                  final_score=round(final, 6), passed=bool(final >= contract['pass_threshold']))
    return result


def evaluate(answer_path, data, analysis_path=None, truth=None):
    D = load_data(data); D['data_dir'] = str(data)
    answer, findings, error = load_answer(answer_path)
    try: analysis = Path(analysis_path).read_text() if analysis_path else ''
    except (OSError, UnicodeError): analysis = ''
    result = assess(answer, D, analysis, truth, findings)
    if error: result['automatic_zero'] = error
    return result


def write_result(result, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    (out/'rubric_results.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    text = '# Thermodynamic prediction grading\n\nScore: '+str(result['final_score'])+'; passed: '+str(result['passed'])+'.\n\n'
    text += 'Artifact grading does not establish isolated pipeline execution.\n\n'
    text += '| Binder or condition | Metric | Value | Threshold | Passed |\n|---|---|---:|---:|---|\n'
    for g in result.get('scientific_gates', []): text += '|{protein}|{metric}|{value}|{threshold}|{passed}|\n'.format(**g)
    (out/'rubric_results.md').write_text(text)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--answer', type=Path, required=True)
    p.add_argument('--analysis', type=Path); p.add_argument('--data', type=Path, default=HERE.parent/'task/data')
    p.add_argument('--output-dir', type=Path, required=True); a = p.parse_args()
    r = evaluate(a.answer, a.data, a.analysis); write_result(r, a.output_dir)
    print(json.dumps({'final_score': r['final_score'], 'passed': r['passed'], 'failed_gates': r.get('failed_gates')}))
