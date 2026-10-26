"""Deterministic synthetic equilibrium library and capture experiments."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import csv
import hashlib
import json
import numpy as np
from model import features, occupancy, slope

ROOT = Path(__file__).resolve().parents[2]
CASE = 'ALS_THERMODYNAMIC_DESIGN_004'


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')


def update_manifest(data):
    files = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(data.iterdir()) if p.is_file() and p.name != 'data_manifest.json'}
    write_json(data/'data_manifest.json', {'case_id': CASE, 'files': files})


def generate(root=ROOT, seed=881472, truth_seed_offset=0):
    root = Path(root)
    data = root/'task/data'
    data.mkdir(parents=True, exist_ok=True)
    private = root/'expert_solution/private'
    private.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    positions = list(range(1, 21))
    seen = {0, *[1 << i for i in range(20)]}
    while len(seen) < 1400:
        idx = rng.choice(20, size=int(rng.integers(2, 9)), replace=False)
        seen.add(sum(1 << int(i) for i in idx))
    screen = sorted(seen)
    while len(seen) < 16384:
        idx = rng.choice(20, size=int(rng.integers(6, 19)), replace=False)
        seen.add(sum(1 << int(i) for i in idx))
    codes = np.array(sorted(seen), dtype=int)
    rng.shuffle(codes)
    bits = ((codes[:, None] >> np.arange(20)) & 1).astype(float)
    rows = [{'variant_id': 'v'+format(code, '05x'), 'mutations': ''.join(str(int(x)) for x in bit),
             'role': 'screen' if int(code) in screen else 'candidate'} for code, bit in zip(codes, bits)]
    with (data/'variants.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    conditions = []
    for u in [0.0, .7, 1.4]:
        for reporter in ['A', 'B']:
            for c in [.15, 2.0]:
                conditions.append(dict(id='s%02d' % len(conditions), urea=u,
                                       ligand_a=c if reporter == 'A' else 0.0,
                                       ligand_b=c if reporter == 'B' else 0.0, reporter=reporter))
    challenges = [dict(id='q0', urea=-.7, ligand_a=.4, ligand_b=.7),
                  dict(id='q1', urea=-.2, ligand_a=1., ligand_b=3.),
                  dict(id='q2', urea=.4, ligand_a=2., ligand_b=10.),
                  dict(id='q3', urea=1., ligand_a=5., ligand_b=20.)]
    proteins, truth = [], {}
    X = features(bits)
    train = np.array([i for i, r in enumerate(rows) if r['role'] == 'screen'])
    calibrations = []
    controls = []
    for c in conditions:
        bg = float(rng.uniform(.008, .018)); ceiling = float(rng.uniform(.962, .985))
        calibrations.append(dict(id=c['id'], background=bg, ceiling=ceiling))
        for i, fraction in enumerate([0., .1, .35, .7, 1.]):
            n = 2000000000
            k = int(rng.binomial(n, bg+(ceiling-bg)*fraction))
            controls.append([c['id'], 'control_%02d' % i, fraction, n, k])
    with (data/'calibration_counts.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['condition_id', 'control_id', 'bound_fraction', 'trials', 'captured']); w.writerows(controls)
    bg = np.array([c['background'] for c in calibrations]); amp = np.array([c['ceiling']-c['background'] for c in calibrations])
    counts = []
    for seed_i in [104, 205, 306, 407, 508, 609]:
        r = np.random.default_rng(seed_i)
        pid = 'binder_'+hashlib.sha256(('equilibrium-'+str(seed_i)).encode()).hexdigest()[:8]
        info = dict(id=pid, m0=1.08, mutation_m_shift=np.round(r.uniform(-.035, .035, 20), 6).tolist())
        proteins.append(info)
        beta = r.normal(0, .12, (3, X.shape[1]))
        beta[:, 0] = [1.4, .5, 1.0]
        beta[:, 1:21] = r.normal([.3, .03, .02], [.6, .4, .4], (20, 3)).T
        for j in range(3):
            beta[j, r.choice(np.arange(21, X.shape[1]), 10, replace=False)] += r.uniform(-1., 1., 10)
        if truth_seed_offset:
            perturb = np.random.default_rng(seed_i+100003*truth_seed_offset)
            beta += perturb.normal(0, .03, beta.shape)
            beta[:, 0] += [-.4, .8, -.7]
        energy = X@beta.T
        pa, pb, _ = occupancy(energy[train], slope(bits[train], info), conditions)
        signal = np.where(np.array([c['reporter'] == 'A' for c in conditions]), pa, pb)
        q = bg+amp*signal
        n = r.integers(25000000, 75000001, q.shape)
        k = r.binomial(n, q)
        for ii, row_i in enumerate(train):
            for jj, c in enumerate(conditions):
                counts.append([pid, rows[row_i]['variant_id'], c['id'], int(n[ii, jj]), int(k[ii, jj])])
        truth[pid] = dict(coefficients=beta.tolist())
    # Input row order conveys no additional relations.
    rng.shuffle(counts)
    with (data/'capture_counts.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['protein_id', 'variant_id', 'condition_id', 'trials', 'captured']); w.writerows(counts)
    meta = dict(case_id=CASE, positions=positions, energy_columns=['fold', 'bind_a', 'bind_b'], urea_baseline_molar=1.0,
                n_variants=len(rows), n_screen=len(train), proteins=proteins,
                screen_conditions=conditions, challenge_conditions=challenges,
                design={'mutation_cost': .003, 'utility': 'apo_folded * min(challenge_a) - mutation_cost * mutation_count'},
                acceptance_thresholds={'energy_rmse_max': .30, 'energy_p95_max': .60,
                                       'apo_rmse_max': .025, 'challenge_rmse_max': .020,
                                       'challenge_max_abs_max': .12, 'design_regret_max': .030},
                report_tolerances={'capture_deviance_per_observation': .05, 'capture_rmse': 1e-6,
                                   'mean_apo_folded': 1e-6, 'mean_worst_a': 1e-6})
    write_json(data/'study_metadata.json', meta)
    write_json(data/'source_provenance.json', dict(case_id=CASE, origin='Original synthetic equilibrium and binomial capture simulation',
              system='Nonclinical, dimensionless protein mutation library; no patient or external sequence data',
              model='Four-state competitive binding with genotype-dependent denaturation and quadratic sequence energies',
              randomization='Independent binomial capture draws conditional on sequence, condition, and control fraction',
              inference_inputs='Only task/data; simulation parameters and generator are expert-only'))
    write_json(private/'truth.json', dict(case_id=CASE, proteins=truth, calibration=calibrations,
                                        seed=seed, truth_seed_offset=truth_seed_offset))
    update_manifest(data)
    return meta


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, default=ROOT); p.add_argument('--seed', type=int, default=881472)
    p.add_argument('--truth-seed-offset', type=int, default=0); a = p.parse_args()
    generate(a.root, a.seed, a.truth_seed_offset)
