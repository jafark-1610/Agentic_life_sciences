"""Population moments, compatible microscopic cycle generators, and first passage."""
import json
from pathlib import Path
from itertools import product
import numpy as np
from scipy.linalg import expm, logm, eigh


def read_json(path):
    return json.loads(Path(path).read_text())


def load_data(data):
    data = Path(data)
    meta = read_json(data/'study_metadata.json')
    protocols = read_json(data/'protocols.json')
    panels = []
    for p in meta['preparations']:
        with np.load(data/p['file'], allow_pickle=False) as arrays:
            values = {key: arrays[key].copy() for key in arrays.files}
        panels.append(dict(id=p['id'], arrays=values, protocol=protocols[p['id']]))
    return dict(meta=meta, panels=panels, data_dir=str(data))


def generator(exchange, fb):
    m = len(exchange)
    Q = np.kron(exchange, np.ones((3, 3))/3)
    for g, (f, b) in enumerate(fb):
        for phase in range(3):
            i = 3*g+phase
            Q[i, i] = exchange[g, g]-f-b
            Q[i, 3*g+(phase+1)%3] = f
            Q[i, 3*g+(phase-1)%3] = b
    return Q


def observable(Q, response, frame_time):
    m = len(Q)//3
    return ((expm(Q*frame_time)[np.arange(m)*3]@response)/m).ravel()


def moments(A, weights):
    return (A@weights, (A*weights)@A.T,
            np.einsum('ia,ja,ka,a->ijk', A, A, A, weights, optimize=True))


def decompose(arrays, rank, contraction):
    eig, U = eigh(arrays['moment2'])
    eig, U = eig[-rank:], U[:, -rank:]
    assert eig.min() > 0
    W = U/np.sqrt(eig)
    white = np.einsum('ijk,ia,jb,kc->abc', arrays['moment3'], W, W, W, optimize=True)
    contracted = np.einsum('abc,c->ab', white, np.array(contraction))
    _, B = eigh(contracted)
    raw = (U*np.sqrt(eig))@B
    normalizers = raw.sum(axis=0)
    weights = normalizers**2
    A = raw/normalizers
    m, n = arrays['response'].shape[0]//3, arrays['response'].shape[0]
    ordering = np.argsort(A.reshape(m, n, rank)[:, :3, :].sum(axis=(0, 1)))
    return weights[ordering], A[:, ordering]


def compatible_family(weights, A, arrays, meta):
    m = meta['modules']; n = 3*m; dt = meta['frame_time']
    phase_vector = np.exp(2j*np.pi*np.arange(3)/3)
    inv_response = np.linalg.inv(arrays['response'])
    families = []
    for h in range(meta['subtypes']):
        P0 = (A[:, h].reshape(m, n)*m)@inv_response
        module_P = P0.reshape(m, m, 3).sum(axis=2)
        exchange = np.real_if_close(logm(module_P)/dt, tol=1000).real
        spectral = np.array([P0[g, 3*g:3*g+3]@phase_vector for g in range(m)])
        sums = -(np.log(np.abs(spectral))/dt-np.diag(exchange))/1.5
        phases = np.angle(spectral)
        lower, upper = meta['rate_bounds']['cycle_rate']
        branches = []
        for s, phase in zip(sums, phases):
            flo = max(lower, s-upper); fhi = min(upper, s-lower)
            klo = int(np.ceil(((2*flo-s)*np.sqrt(3)/2*dt-phase)/(2*np.pi)-1e-8))
            khi = int(np.floor(((2*fhi-s)*np.sqrt(3)/2*dt-phase)/(2*np.pi)+1e-8))
            branches.append(range(klo, khi+1))
        models, codes = [], []
        for code in product(*branches):
            difference = (phases+2*np.pi*np.array(code))/(dt*np.sqrt(3)/2)
            fb = np.column_stack([(sums+difference)/2, (sums-difference)/2])
            assert fb.min() >= lower-1e-6 and fb.max() <= upper+1e-6
            models.append(fb); codes.append(list(code))
        assert models, 'No compatible positive generator'
        families.append(dict(weight=float(weights[h]), exchange=exchange, sums=sums, phases=phases,
                             models=np.array(models), codes=codes))
    return families


def first_passage(Q, action, target, duration, endpoint=False):
    n = len(Q)
    qa = Q*np.array(action['multiplier'])
    np.fill_diagonal(qa, 0)
    np.fill_diagonal(qa, -qa.sum(axis=1))
    loss = np.array(action['loss_rate'])
    if endpoint:
        transition = expm((qa-np.diag(loss))*duration)
        return transition[:, target].sum(axis=1), 1-transition.sum(axis=1)
    transient = [i for i in range(n) if i not in target]
    r = len(transient)
    augmented = np.zeros((r+2, r+2))
    augmented[:r, :r] = qa[np.ix_(transient, transient)]-np.diag(loss[transient])
    augmented[:r, r] = qa[np.ix_(transient, target)].sum(axis=1)
    augmented[:r, r+1] = loss[transient]
    transition = expm(augmented*duration)
    hit, dead = np.zeros(n), np.zeros(n)
    hit[target] = 1
    hit[transient], dead[transient] = transition[:r, r], transition[:r, r+1]
    return hit, dead


def stationary_epr(Q):
    n = len(Q)
    pi = np.linalg.lstsq(np.vstack([Q.T, np.ones(n)]), np.r_[np.zeros(n), 1.], rcond=None)[0]
    flow = pi[:, None]*Q
    ii = np.triu_indices(n, 1)
    a, b = flow[ii], flow.T[ii]
    return float(np.sum((a-b)*np.log(a/b)))


def candidate_statistics(family, protocol, policies, endpoint=False):
    actions = protocol['actions']; choices = np.array([p['actions'] for p in policies])
    rho = np.array(protocol['initial_distribution'])
    killing = np.array(protocol['pre_loss_rate'])
    selection = np.array(protocol['selection_probability'])
    observation = np.array(protocol['observation'])
    hit_rows, loss_rows, cost_rows, den, entropy, flux = [], [], [], [], [], []
    exchange = family['exchange']
    module_pi = np.linalg.lstsq(np.vstack([exchange.T, np.ones(len(exchange))]), np.r_[np.zeros(len(exchange)), 1.], rcond=None)[0]
    for fb in family['models']:
        Q = generator(family['exchange'], fb)
        selected = (rho@expm((Q-np.diag(killing))*protocol['screen_time']))*selection
        den.append(selected.sum())
        mass = selected@observation
        hit, loss, cost = [], [], []
        for action in actions:
            h, l = first_passage(Q, action, protocol['target_states'], protocol['followup_time'], endpoint)
            hit.append(selected@(observation*h[:, None]))
            loss.append(selected@(observation*l[:, None]))
            cost.append(mass*action['resource_cost'])
        hit, loss, cost = np.array(hit), np.array(loss), np.array(cost)
        columns = np.arange(observation.shape[1])
        hit_rows.append(hit[choices, columns].sum(axis=1))
        loss_rows.append(loss[choices, columns].sum(axis=1))
        cost_rows.append(cost[choices, columns].sum(axis=1))
        entropy.append(stationary_epr(Q))
        flux.append(float(np.dot(module_pi/3, fb[:, 0]-fb[:, 1])))
    hit, loss, cost = np.array(hit_rows), np.array(loss_rows), np.array(cost_rows)
    d = np.array(den)
    base = protocol['benchmark_policy_index']
    gain = hit-hit[:, [base]]-protocol['loss_penalty']*(loss-loss[:, [base]])
    net = gain-protocol['resource_penalty']*cost
    return dict(success=hit, loss=loss, cost=cost, gain=gain, net=net, d=d,
                retained_epr=(d*np.array(entropy))[:, None], flux=np.array(flux))
