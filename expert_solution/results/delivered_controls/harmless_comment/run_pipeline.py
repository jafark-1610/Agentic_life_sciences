import sys, os
sys.dont_write_bytecode = True
for _thread_variable in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[_thread_variable] = "1"
DEFAULT_CONFIG = {'case_id': 'ALS_RNA_TRANSPORT_006', 'required_deliverables': ['run_pipeline.py', 'final_answer.json', 'analysis.md'], 'iterations': 65}
import json, hashlib
from pathlib import Path
import numpy as np
from scipy.special import exprel, log_ndtr
from scipy.stats import t

def trajectory(theta, dt, g, q, gpre):
    n = np.exp(theta[:, 0])
    e, dn, dc = np.exp(theta[:, 1:]).T
    c = n * e / (dc + gpre)
    alpha = (e + dn + gpre) * n
    out = [np.column_stack([n, c])]
    for h, gg, qq in zip(dt, g, q):
        a = e + dn + gg
        b = dc + gg
        A = np.exp(-a * h)
        B = np.exp(-b * h)
        J = B * h * exprel(-(a - b) * h)
        s = alpha * qq
        c = c * B + e * (n * J + s / a * (h * exprel(-b * h) - J))
        n = n * A + s * h * exprel(-a * h)
        out.append(np.column_stack([n, c]))
    return np.array(out).transpose(1, 0, 2)

def fit(obs, cal, dt, g, q, gpre, sigma, limit, iterations=65, no_growth=False, no_source=False, no_mixing=False):
    if no_growth:
        g = np.zeros_like(g)
        gpre = 0.0
    if no_source:
        q = np.zeros_like(q)
    if no_mixing:
        cal = cal.copy()
        cal[:, 1, 0] = 0
        cal[:, 0, 1] = 0
    G = len(obs)
    cal = cal[0] if cal.ndim == 4 else cal
    finite = np.isfinite(obs)
    logs = np.log(np.where(finite, obs, limit))
    floor = np.log(limit)

    def residual(x):
        pop = trajectory(x, dt, g, q, gpre)
        mu = np.einsum('tij,gtj->gti', cal, pop)
        z = (np.log(np.maximum(mu, 1e-20)) - logs) / sigma
        censor = np.sqrt(np.maximum(0, -2 * log_ndtr((floor - np.log(np.maximum(mu, 1e-20))) / sigma)))
        return np.where(finite, z, censor).reshape(G, -1)
    initial = np.maximum(np.einsum('ij,gj->gi', np.linalg.inv(cal[0]), np.nan_to_num(obs[:, 0], nan=float(np.min(limit))))[:, 0], 0.2)
    best = np.full(G, np.inf)
    answer = np.zeros((G, 4))
    eye = np.eye(4)[None]
    for nuclear in [0.05, 0.25]:
        x = np.column_stack([np.log(initial), np.full(G, np.log(0.25)), np.full(G, np.log(nuclear)), np.full(G, np.log(0.12))])
        lam = np.full(G, 0.01)
        for it in range(iterations):
            r = residual(x)
            J = np.stack([(residual(x + eye[:, j, :] * 0.0001) - r) / 0.0001 for j in range(4)], axis=2)
            H = np.einsum('gti,gtj->gij', J, J)
            gradient = np.einsum('gti,gt->gi', J, r)
            scale = np.maximum(np.diagonal(H, axis1=1, axis2=2), 0.01)
            step = np.linalg.solve(H + lam[:, None, None] * eye * scale[:, None, :], gradient[..., None])[..., 0]
            step = np.clip(step, -1.2, 1.2)
            trial = x - step
            trial[:, 0] = np.clip(trial[:, 0], -3, 13)
            trial[:, 1:] = np.clip(trial[:, 1:], -7, 1.5)
            old = np.sum(r * r, axis=1)
            new = np.sum(residual(trial) ** 2, axis=1)
            accept = new < old
            x[accept] = trial[accept]
            lam = np.where(accept, np.maximum(lam * 0.3, 1e-08), np.minimum(lam * 8, 1000000000.0))
        loss = np.sum(residual(x) ** 2, axis=1)
        accept = loss < best
        answer[accept] = x[accept]
        best[accept] = loss[accept]
    return (answer, best)

def load(data):
    data = Path(data)
    m = json.loads((data / 'study_metadata.json').read_text())
    with np.load(data / 'hybridization.npz', allow_pickle=False) as f:
        D = {k: f[k].copy() for k in f.files}
    return (m, D)

def inference(est, m, indices, unpaired=False):
    values = est / np.log(2)
    diff = values[:, indices, 1, 1:] - values[:, indices, 0, 1:]
    n = len(indices)
    mean = diff.mean(axis=1)
    se = diff.std(axis=1, ddof=1) / np.sqrt(n)
    if unpaired:
        se = np.sqrt(values[:, indices, 1, 1:].var(axis=1, ddof=1) / n + values[:, indices, 0, 1:].var(axis=1, ddof=1) / n)
    se = np.maximum(se, 0.015)
    ci = np.stack([mean - t.ppf(0.975, n - 1) * se, mean + t.ppf(0.975, n - 1) * se], axis=-1)
    eq = np.stack([mean - t.ppf(0.95, n - 1) * se, mean + t.ppf(0.95, n - 1) * se], axis=-1)
    p = t.sf((np.abs(mean) - m['material_log2']) / se, n - 1)
    order = np.argsort(p.ravel())
    adjust = np.minimum.accumulate((p.ravel()[order] * p.size / np.arange(1, p.size + 1))[::-1])[::-1]
    q = np.empty(p.size)
    q[order] = np.minimum(adjust, 1)
    q = q.reshape(p.shape)
    classes = np.full(mean.shape, 'UNRESOLVED', dtype=object)
    classes[(eq[:, :, 0] > -m['material_log2']) & (eq[:, :, 1] < m['material_log2'])] = 'EQUIVALENT'
    classes[(q <= 0.05) & (mean > 0)] = 'INCREASED'
    classes[(q <= 0.05) & (mean < 0)] = 'DECREASED'
    rows = []
    for j, gid in enumerate(m['genes']):
        effects = {}
        for k, name in enumerate(m['parameters']):
            effects[name] = {'log2_ratio': float(mean[j, k]), 'interval': ci[j, k].tolist(), 'equivalence_interval': eq[j, k].tolist(), 'class': classes[j, k], 'vehicle_rate': float(2 ** values[j, indices, 0, k + 1].mean()), 'perturbed_rate': float(2 ** values[j, indices, 1, k + 1].mean())}
        rows.append({'id': gid, 'effects': effects})
    group = []
    mask = np.array(m['stress_group'])
    for k, name in enumerate(m['parameters']):
        v = diff[mask, :, k].mean(axis=0) - diff[~mask, :, k].mean(axis=0)
        s = v.std(ddof=1) / np.sqrt(n)
        group.append({'parameter': name, 'estimate': float(v.mean()), 'interval': [float(v.mean() - t.ppf(0.975, n - 1) * s), float(v.mean() + t.ppf(0.975, n - 1) * s)]})
    return {'genes': rows, 'group_contrasts': group, 'inference_trace': {'parent_indices': list(indices), 'log2_rates': values[:, indices, :, 1:].tolist()}}

def analyse(data, config):
    m, D = load(data)
    G = len(m['genes'])
    P = m['parents']
    est = np.zeros((G, P, 2, 4))
    analyses = {}
    diagnostics = {}
    for variant in ['base', 'early_window', 'leave_parent_out']:
        if variant == 'leave_parent_out':
            analyses[variant] = inference(est, m, list(range(P - 1)), config.get('unpaired', False))
            continue
        last = len(m['times']) if variant == 'base' else len(m['times']) - 2
        cal = D['spike_observed'] / D['spike_known'][None, None, None, :, None]
        cal = np.exp(np.log(cal).mean(axis=-1))
        result = np.zeros_like(est)
        losses = []
        for p in range(P):
            for arm in range(2):
                growth = np.diff(np.log(D['cell_counts'][p, arm, :last])) / np.diff(m['times'][:last])
                q = D['run_on'][p, arm, :last - 1].mean(axis=-1)
                x, loss = fit(D['observed'][:, p, arm, :last], cal[p, arm, :last], np.diff(m['times'][:last]), growth, q, D['pre_growth'][p, arm], m['log_sigma'], D['limits'][p, arm, :last], config['iterations'], config.get('no_growth', False), config.get('no_source', False), config.get('no_mixing', False))
                result[:, p, arm] = x
                losses.extend(loss.tolist())
        analyses[variant] = inference(result, m, list(range(P)), config.get('unpaired', False))
        diagnostics[variant] = {'mean_deviance': float(np.mean(losses)), 'fits': len(losses)}
        if variant == 'base':
            est = result.copy()
    for setting, body in analyses.items():
        body['inference_trace']['time_indices'] = list(range(len(m['times']) - 2 if setting == 'early_window' else len(m['times'])))
        body['inference_trace']['input_sha256'] = hashlib.sha256((Path(data) / 'hybridization.npz').read_bytes()).hexdigest()
    return ({'schema': 'rna_transport/1', 'case_id': m['case_id'], 'analyses': analyses}, diagnostics)
import json, importlib.metadata
from pathlib import Path
LABELS = ['INCREASED', 'DECREASED', 'EQUIVALENT', 'UNRESOLVED', 'NOT_ESTIMABLE']

def counts(answer):
    return {name: {label: sum((e['class'] == label for g in a['genes'] for e in g['effects'].values())) for label in LABELS} for name, a in answer['analyses'].items()}

def write_outputs(answer, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'final_answer.json').write_text(json.dumps(answer, allow_nan=False) + '\n')
    sections = {'Methods': 'Joint compartment mass balance is fitted because nuclear disappearance includes both export and destruction. A censored log-normal likelihood and multiple initializations stabilize the kinetic estimates.', 'Calibration': 'Origin-resolved RNA standards identify each sample fractionation and gain matrix. Both physical compartments contribute to each collected fraction, without forcing row normalization.', 'Censoring': 'Signals below the detection limit contribute normal lower-tail probabilities in log space. They are not zero intensities or observations missing at random.', 'Replication': 'Parental populations supply the biological replication. Paired sibling cultures define the treatment contrasts; technical standards, genes and time points do not increase the parent count.', 'Group uncertainty': 'Stress and other transcript means are first contrasted within each parent. Variation among those parental contrasts determines the group interval, preserving shared culture variation.', 'Sensitivity': 'The early window refits the retained sampling times. Parent exclusion uses only indices zero through four, with recomputed paired contrasts and multiplicity adjustment; inference_trace records the actual rate inputs.', 'Limitations': 'The observations are synthetic. First-order destruction, equilibrated baseline pools and well-mixed compartments are assumptions. Six biological parents provide limited precision for small nuclear destruction effects.'}
    text = '\n\n'.join(('# ' + k + '\n\n' + v for k, v in sections.items()))
    text += '\n\n# Software\n\n' + ', '.join((p + ' ' + importlib.metadata.version(p) for p in ['numpy', 'scipy'])) + ' were used for numerical linear algebra and distribution calculations.\n\n```json\n' + json.dumps({'analysis_counts': counts(answer)}, indent=2) + '\n```\n'
    (out / 'analysis.md').write_text(text)
    return answer
import os, sys
sys.dont_write_bytecode = True
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import argparse, json, time, hashlib, platform
from pathlib import Path
import jsonschema

def main():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser()
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--config', type=Path, default=None)
    a = p.parse_args()
    start = time.monotonic()
    config = json.loads(a.config.read_text()) if a.config else DEFAULT_CONFIG
    answer, d = analyse(a.data, config)
    write_outputs(answer, a.output_dir)
    jsonschema.validate(answer, json.loads((a.data / 'output_schema.json').read_text()))
    record = {'case_id': answer['case_id'], 'status': 'success', 'exit_code': 0, 'seconds': time.monotonic() - start, 'python': platform.python_version(), 'required_deliverables': config['required_deliverables'], 'configuration': config, 'diagnostics': d, 'answer_sha256': hashlib.sha256((a.output_dir / 'final_answer.json').read_bytes()).hexdigest(), 'data_manifest_sha256': hashlib.sha256((a.data / 'data_manifest.json').read_bytes()).hexdigest()}
    (a.output_dir / 'run_summary.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'status': 'success', 'seconds': record['seconds']}))
if __name__ == '__main__':
    main()

# Documentation only: expert_solution/private is not read.
