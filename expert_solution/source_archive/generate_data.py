"""Original persistent-subtype cycle experiments, regenerated deterministically."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import io
import hashlib
import json
import zipfile
from itertools import product
import numpy as np
from kinetics import generator, observable, moments

ROOT = Path(__file__).resolve().parents[2]
CASE = 'ALS_HIDDEN_CYCLE_005'


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')


def save_npz(path, arrays):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, a in sorted(arrays.items()):
            stream = io.BytesIO(); np.lib.format.write_array(stream, a, allow_pickle=False)
            item = zipfile.ZipInfo(name+'.npy', (2026, 1, 1, 0, 0, 0)); item.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(item, stream.getvalue(), compresslevel=9)


def update_manifest(data):
    files = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(data.iterdir()) if p.is_file() and p.name != 'data_manifest.json'}
    write_json(data/'data_manifest.json', dict(case_id=CASE, files=files))


def make_protocol(seed, modules=6):
    rng = np.random.default_rng(seed+100000); n = modules*3
    rho = np.zeros(n); rho[0] = .55; rho[6] = .25; rho[15] = .20
    preloss = rng.uniform(.15, .65, n)
    selection = np.tile([.22, .84, .35], modules)*rng.uniform(.8, 1.1, n)
    H = rng.uniform(.4, .6, (n, 3))
    for i in range(n):
        H[i, (i//3)%3] += 1.2; H[i, i%3] += rng.uniform(0., .4)
    H /= H.sum(axis=1)[:, None]
    actions = []
    for a in range(4):
        mult = np.ones((n, n))
        for g in range(modules):
            for phase in range(3):
                i = 3*g+phase
                if a == 1: mult[i, 3*g+(phase+1)%3] = 4.5
                if a == 2: mult[i, 3*g+(phase-1)%3] = 4.5
                if a == 3:
                    mult[i, 3*g+(phase+1)%3] = 2.4
                    mult[i, 3*g+(phase-1)%3] = 2.4
        rng.uniform(1.1, 2., n)
        actions.append(dict(id='a'+str(a), multiplier=mult.tolist(), resource_cost=[0., .025, .025, .10][a]))
    loss = rng.uniform(1.1, 2., n).tolist()
    for action in actions: action['loss_rate'] = loss
    # Relabel sensor categories and active drugs independently; the physics remains fully supplied.
    perm = rng.permutation(3)
    H = H[:, perm]
    drug_perm = [0, *list(1+rng.permutation(3))]
    actions = [actions[i] for i in drug_perm]
    for i, action in enumerate(actions): action['id'] = 'a'+str(i)
    return dict(initial_distribution=rho.tolist(), pre_loss_rate=preloss.tolist(),
                selection_probability=selection.tolist(), observation=H.tolist(), target_states=[2, 14],
                actions=actions, screen_time=.075, followup_time=.18, loss_penalty=.35,
                resource_penalty=.65, benchmark_policy_index=0)


def generate(root=ROOT, perturbation=0):
    root = Path(root); data = root/'task/data'; data.mkdir(parents=True, exist_ok=True)
    preparations, truth, protocols = [], {}, {}
    m, n, rank = 6, 18, 3
    for seed in range(751, 759):
        rng = np.random.default_rng(seed+10007*perturbation)
        pid = 'prep_'+hashlib.sha256(('persistent-enzyme-'+str(seed)).encode()).hexdigest()[:8]
        C = .91*np.eye(n)+.09*rng.dirichlet(np.ones(n), n)
        w = rng.dirichlet([5, 6, 7]); Rs, sums, phases, columns = [], [], [], []
        for h in range(rank):
            pi = rng.dirichlet(np.ones(m)*7); pi[0] = [.035, .25, .55][h]
            pi[1:] *= (1-pi[0])/pi[1:].sum()
            R = [.22, .58, 1.05][h]*(np.ones((m, 1))*pi-np.eye(m))
            R += rng.uniform(.001, .008, (m, m)); np.fill_diagonal(R, 0); np.fill_diagonal(R, -R.sum(axis=1))
            s = rng.uniform(8.5, 9.3, m); phase = rng.uniform(-.65, .65, m)
            f = (s+phase/(np.sqrt(3)/2))/2; b = s-f
            Q = generator(R, np.column_stack([f, b]))
            columns.append(observable(Q, C, 1.))
            Rs.append(R.tolist()); sums.append(s.tolist()); phases.append(phase.tolist())
        A = np.array(columns).T; one, two, three = moments(A, w)
        path = pid+'_moments.npz'
        save_npz(data/path, dict(moment1=one, moment2=two, moment3=three, response=C))
        preparations.append(dict(id=pid, file=path))
        truth[pid] = dict(weights=w.tolist(), exchange=Rs, sums=sums, phases=phases)
        protocols[pid] = make_protocol(seed+10007*perturbation)
        actual_codes = rng.integers(-1, 2, (rank, m)); flux = 0.
        for h in range(rank):
            R = np.array(Rs[h]); pi = np.linalg.lstsq(np.vstack([R.T, np.ones(m)]), np.r_[np.zeros(m), 1.], rcond=None)[0]
            difference = (np.array(phases[h])+2*np.pi*actual_codes[h])/(np.sqrt(3)/2)
            flux += w[h]*np.dot(pi/3, difference)
        center = round(float(flux), 3)
        protocols[pid]['bulk_turnover'] = {'lower': center-.0005, 'upper': center+.0005}
        truth[pid]['actual_branch_codes'] = actual_codes.tolist()
    policies = [dict(id='p%02d' % i, actions=list(a)) for i, a in enumerate(product(range(4), repeat=3))]
    meta = dict(case_id=CASE, modules=m, phases_per_module=3, states=n, subtypes=rank,
                frame_time=1., outcome_dimension=m*n, preparations=preparations, policies=policies,
                rate_bounds={'cycle_rate': [.10, 9.6], 'cycle_sum': [8., 9.8],
                             'exchange_offdiag': [.0001, .7], 'exchange_exit_max': 1.2},
                tolerances={'mixture': .00005, 'exchange': .00005, 'cycle_bounds': .003,
                            'retention': .0015, 'epr': .02, 'probability_bounds': .0015,
                            'gain_bounds': .002, 'net_bounds': .002, 'choice_regret': .003,
                            'witness_rates': .003, 'witness_endpoint': .003, 'witness_turnover': .00001},
                report_tolerances={'moment2_max_abs_error': 1e-7, 'moment3_max_abs_error': 1e-7,
                                   'lower_net_witness_value': 1e-6, 'upper_net_witness_value': 1e-6,
                                   'lower_selection_probability': 1e-6, 'upper_selection_probability': 1e-6})
    write_json(data/'study_metadata.json', meta)
    write_json(data/'protocols.json', protocols)
    write_json(data/'source_provenance.json', dict(case_id=CASE, origin='Original synthetic population experiments',
               measurements='Exact three-replicate reset-outcome population laws stored in float64',
               system='Persistent enzyme subtypes with exchange-coupled mechanochemical cycles',
               scope='Nonclinical method simulation with no external data or annotations'))
    write_json(root/'expert_solution/private/truth.json', dict(case_id=CASE, preparations=truth, perturbation=perturbation))
    update_manifest(data)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, default=ROOT); p.add_argument('--perturbation', type=int, default=0)
    a = p.parse_args(); generate(a.root, a.perturbation)
