"""Independent weighted apparent-energy inference and direct partition arithmetic."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import csv
import json
import numpy as np
from scipy.optimize import least_squares
from scipy.special import expit


def infer(data):
    data = Path(data)
    meta = json.loads((data/'study_metadata.json').read_text())
    def csv_rows(name):
        with (data/name).open() as f: return list(csv.DictReader(f))
    variants = csv_rows('variants.csv')
    bits = np.array([[int(b) for b in v['mutations']] for v in variants])
    pairs = [(i, j) for j in range(bits.shape[1]) for i in range(j)]
    # Different feature order and constant placement from the count-likelihood pipeline.
    X = np.column_stack([*[bits[:, i]*bits[:, j] for i, j in pairs], bits, np.ones(len(bits))])
    train = [i for i, v in enumerate(variants) if v['role'] == 'screen']
    qi, rr = np.linalg.qr(X[train], mode='reduced')
    q, r = qi*np.sqrt(len(train)), rr/np.sqrt(len(train))
    observations = csv_rows('capture_counts.csv'); controls = csv_rows('calibration_counts.csv')
    index = {variants[i]['variant_id']: j for j, i in enumerate(train)}
    conditions = meta['screen_conditions']; ci = {c['id']: i for i, c in enumerate(conditions)}
    cal = []
    for c in conditions:
        rows = [v for v in controls if v['condition_id'] == c['id']]
        # Endpoint-only calibration is statistically less efficient but independently valid.
        ends = [next(v for v in rows if float(v['bound_fraction']) == t) for t in [0, 1]]
        cal.append(dict(id=c['id'], background=int(ends[0]['captured'])/int(ends[0]['trials']),
                        ceiling=int(ends[1]['captured'])/int(ends[1]['trials'])))
    bg = np.array([v['background'] for v in cal]); amp = np.array([v['ceiling']-v['background'] for v in cal])
    concentrations = np.array([c['ligand_a']+c['ligand_b'] for c in conditions])
    urea = np.array([c['urea'] for c in conditions]); is_b = np.array([c['reporter'] == 'B' for c in conditions])
    out, info = [], []
    for protein in meta['proteins']:
        rows = [v for v in observations if v['protein_id'] == protein['id']]
        n, k = np.zeros((len(train), len(conditions))), np.zeros((len(train), len(conditions)))
        for row in rows:
            i, j = index[row['variant_id']], ci[row['condition_id']]
            n[i, j], k[i, j] = int(row['trials']), int(row['captured'])
        observed = k/n
        p = np.clip((observed-bg)/amp, 1e-7, 1-1e-7)
        h = np.log(concentrations)-np.log(p)+np.log1p(-p)
        weights = np.sqrt(n)*amp*p*(1-p)/np.sqrt(observed*(1-observed))
        m = protein['m0']+bits@np.asarray(protein['mutation_m_shift'])
        shifts = m[train, None]*urea
        d = q.shape[1]
        def residual(theta):
            values = q@theta.reshape(3, d).T
            effective = np.logaddexp(0, values[:, 0, None]+shifts)+values[:, 1:][:, is_b.astype(int)]
            return ((effective-h)*weights).ravel()
        def jacobian(theta):
            values = q@theta.reshape(3, d).T
            factors = [expit(values[:, 0, None]+shifts), np.broadcast_to(~is_b, h.shape), np.broadcast_to(is_b, h.shape)]
            return np.concatenate([(q[:, None, :]*(weights*f)[:, :, None]).reshape(-1, d) for f in factors], axis=1)
        t = [np.linalg.lstsq(q, np.full(len(train), 2.), rcond=None)[0]]
        for s in [False, True]:
            mask = is_b == s
            z = h[:, mask]-np.logaddexp(0, 2.+shifts[:, mask])
            w = weights[:, mask]**2
            z = np.sum(z*w, axis=1)/np.sum(w, axis=1)
            t.append(np.linalg.lstsq(q, z, rcond=None)[0])
        fit = least_squares(residual, np.array(t).ravel(), jac=jacobian, method='lm',
                            max_nfev=100, ftol=1e-10, xtol=1e-10, gtol=1e-8)
        coef = np.linalg.solve(r, fit.x.reshape(3, d).T)
        en = X@coef
        apo = 1/(1+np.exp(en[:, 0]))
        predictions = []
        for c in meta['challenge_conditions']:
            ef = np.exp(-en[:, 0]-m*c['urea'])
            a = c['ligand_a']*ef*np.exp(-en[:, 1]); b = c['ligand_b']*ef*np.exp(-en[:, 2])
            predictions.append(a/(1+ef+a+b))
        pa = np.array(predictions).T
        utility = apo*np.min(pa, axis=1)-meta['design']['mutation_cost']*bits.sum(axis=1)
        selected = variants[int(np.argmax(utility))]['variant_id']
        out.append(dict(id=protein['id'], energy=en.tolist(), apo_folded=apo.tolist(), challenge_a=pa.tolist(), selected_variant=selected))
        info.append(dict(id=protein['id'], optimizer_success=bool(fit.success), evaluations=fit.nfev, weighted_residual_mean=float(np.mean(fit.fun**2))))
    return dict(schema='thermodynamic_design/1', case_id=meta['case_id'], calibration=cal, proteins=out), info


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--data', type=Path, required=True); p.add_argument('--output-dir', type=Path, required=True)
    a = p.parse_args(); answer, diagnostics = infer(a.data)
    from artifacts import write_outputs
    from model import load_data
    write_outputs(answer, load_data(a.data), a.output_dir,
                  'Endpoint controls calibrate each capture condition. Weighted apparent-energy residuals are minimized jointly over quadratic genotype energy fields by an independent Levenberg-Marquardt estimator.')
    (a.output_dir/'independent_diagnostics.json').write_text(json.dumps(diagnostics, indent=2)+'\n')
