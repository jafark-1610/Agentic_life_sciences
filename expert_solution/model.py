"""Thermodynamic state probabilities and genotype design matrices."""
import csv
import json
from itertools import combinations
from pathlib import Path
import numpy as np
from scipy.special import expit, logsumexp


def read_json(path):
    return json.loads(Path(path).read_text())


def load_data(data):
    data = Path(data)
    meta = read_json(data / 'study_metadata.json')
    with (data / 'variants.csv').open() as f:
        rows = list(csv.DictReader(f))
    bits = np.array([[int(b) for b in r['mutations']] for r in rows], dtype=float)
    with (data / 'capture_counts.csv').open() as f:
        counts = list(csv.DictReader(f))
    with (data / 'calibration_counts.csv').open() as f:
        controls = list(csv.DictReader(f))
    return dict(meta=meta, rows=rows, bits=bits, counts=counts, controls=controls)


def features(bits):
    pairs = list(combinations(range(bits.shape[1]), 2))
    return np.column_stack([np.ones(len(bits)), bits,
                            *[bits[:, i] * bits[:, j] for i, j in pairs]])


def slope(bits, protein):
    return protein['m0'] + bits @ np.array(protein['mutation_m_shift'])


def occupancy(energy, m, conditions):
    """Four-state partition sum; returns A, B, and total folded probabilities."""
    u = np.array([c['urea'] for c in conditions])
    a = np.array([c['ligand_a'] for c in conditions])
    b = np.array([c['ligand_b'] for c in conditions])
    gf = energy[:, 0, None] + m[:, None] * u
    ga, gb = energy[:, 1, None], energy[:, 2, None]
    with np.errstate(divide='ignore'):
        la = -gf - ga + np.log(a)
        lb = -gf - gb + np.log(b)
    lf = -gf + np.zeros_like(la)
    z = logsumexp(np.stack([np.zeros_like(lf), lf, la, lb]), axis=0)
    pa, pb = np.exp(la-z), np.exp(lb-z)
    folded = np.exp(lf-z) + pa + pb
    return pa, pb, folded


def utility(apo, pa, bits, meta):
    return apo * np.min(pa, axis=1) - meta['design']['mutation_cost'] * bits.sum(axis=1)


def protein_arrays(D, protein):
    train = np.array([i for i, r in enumerate(D['rows']) if r['role'] == 'screen'])
    index = {D['rows'][i]['variant_id']: j for j, i in enumerate(train)}
    ci = {c['id']: j for j, c in enumerate(D['meta']['screen_conditions'])}
    n = np.zeros((len(train), len(ci)), dtype=float)
    k = np.zeros_like(n)
    for r in D['counts']:
        if r['protein_id'] == protein['id']:
            i, j = index[r['variant_id']], ci[r['condition_id']]
            n[i, j], k[i, j] = int(r['trials']), int(r['captured'])
    return train, n, k


def calibration(D):
    out = []
    for c in D['meta']['screen_conditions']:
        rows = [r for r in D['controls'] if r['condition_id'] == c['id']]
        t = np.array([float(r['bound_fraction']) for r in rows])
        n = np.array([int(r['trials']) for r in rows])
        y = np.array([int(r['captured']) for r in rows]) / n
        X = np.column_stack([1-t, t])
        v = np.maximum(y*(1-y), 1e-8)/n
        beta = np.linalg.lstsq(X/np.sqrt(v[:, None]), y/np.sqrt(v), rcond=None)[0]
        out.append(dict(id=c['id'], background=float(beta[0]), ceiling=float(beta[1])))
    return out


def deviance(n, k, q):
    from scipy.special import xlogy
    y = k/n
    q = np.clip(q, 1e-15, 1-1e-15)
    return np.maximum(0, 2*n*(xlogy(y, y/q)+xlogy(1-y, (1-y)/(1-q))))


def evidence(answer, D):
    cal = {c['id']: c for c in answer['calibration']}
    bg = np.array([cal[c['id']]['background'] for c in D['meta']['screen_conditions']])
    ceiling = np.array([cal[c['id']]['ceiling'] for c in D['meta']['screen_conditions']])
    by_id = {p['id']: p for p in answer['proteins']}
    result = []
    for p in D['meta']['proteins']:
        obj = by_id[p['id']]
        train, n, k = protein_arrays(D, p)
        energy = np.asarray(obj['energy'], dtype=float)
        pa, pb, _ = occupancy(energy[train], slope(D['bits'][train], p), D['meta']['screen_conditions'])
        is_a = np.array([c['reporter'] == 'A' for c in D['meta']['screen_conditions']])
        q = bg+(ceiling-bg)*np.where(is_a, pa, pb)
        result.append(dict(id=p['id'], capture_deviance_per_observation=float(deviance(n, k, q).mean()),
                           capture_rmse=float(np.sqrt(np.mean((q-k/n)**2))),
                           mean_apo_folded=float(np.mean(obj['apo_folded'])),
                           mean_worst_a=float(np.mean(np.min(obj['challenge_a'], axis=1)))))
    return result
