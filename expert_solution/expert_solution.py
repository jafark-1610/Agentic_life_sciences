"""Joint count-likelihood inference of quadratic folding and binding landscapes."""
import numpy as np
from scipy.special import expit, xlogy
from scipy.linalg import cho_factor, cho_solve, solve_triangular
from model import (load_data, features, slope, protein_arrays, calibration,
                   occupancy, utility)


def fit_landscape(X, m, n, k, conditions, cal, config):
    ng, d = X.shape
    u = np.array([c['urea'] for c in conditions])
    ligand = np.array([max(c['ligand_a'], c['ligand_b']) for c in conditions])
    species = np.array([int(c['reporter'] == 'B') for c in conditions])
    bg = np.array([c['background'] for c in cal])
    amp = np.array([c['ceiling']-c['background'] for c in cal])
    y = k/n
    Q, R = np.linalg.qr(X, mode='reduced')
    Q *= np.sqrt(ng)
    R /= np.sqrt(ng)
    p = np.clip((y-bg)/amp, 1e-7, 1-1e-7)
    h = np.log(ligand)-np.log(p/(1-p))
    weights = n*(amp*p*(1-p))**2/np.maximum(y*(1-y), 1e-8)
    mu = m[:, None]*u
    grid = np.linspace(config['initial_fold_min'], config['initial_fold_max'], config['initial_fold_grid'])
    losses = np.zeros((ng, len(grid)))
    for j, f in enumerate(grid):
        z = h-np.logaddexp(0, f+mu)
        for s in [0, 1]:
            mask = species == s
            average = np.sum(weights[:, mask]*z[:, mask], axis=1)/np.sum(weights[:, mask], axis=1)
            losses[:, j] += np.sum(weights[:, mask]*(z[:, mask]-average[:, None])**2, axis=1)
    fhat = grid[np.argmin(losses, axis=1)]

    def objective(T, derivatives=False):
        fields = Q@T.T
        F = fields[:, 0, None]+mu
        P = expit(np.log(ligand)-fields[:, 1:][:, species]-np.logaddexp(0, F))
        q = bg+amp*P
        value = float(np.sum(n*(xlogy(y, y/q)+xlogy(1-y, (1-y)/(1-q))))/ng)
        if not derivatives:
            return value
        a = -amp*P*(1-P)
        der = [a*expit(F), a*(species == 0), a*(species == 1)]
        g = np.empty((3, d))
        H = np.empty((3*d, 3*d))
        v, w = n*(q-y)/(q*(1-q))/ng, n/(q*(1-q))/ng
        for i in range(3):
            g[i] = Q.T@np.sum(v*der[i], axis=1)
            for j in range(i+1):
                block = Q.T@(Q*np.sum(w*der[i]*der[j], axis=1)[:, None])
                H[i*d:(i+1)*d, j*d:(j+1)*d] = block
                H[j*d:(j+1)*d, i*d:(i+1)*d] = block.T
        return value, g.ravel(), H

    best = None
    traces = []
    for start in config['starts']:
        fh = fhat if start == 'profile' else np.full(ng, float(start))
        T = [np.linalg.lstsq(Q, fh, rcond=None)[0]]
        for s in [0, 1]:
            mask = species == s
            z = h[:, mask]-np.logaddexp(0, fh[:, None]+mu[:, mask])
            z = np.sum(z*weights[:, mask], axis=1)/np.sum(weights[:, mask], axis=1)
            T.append(np.linalg.lstsq(Q, z, rcond=None)[0])
        T, damping = np.array(T), config['initial_damping']
        accepted = False
        for iteration in range(config['max_iterations']):
            loss, g, H = objective(T, True)
            diag = np.maximum(np.diag(H), .01)
            accepted = False
            for _ in range(24):
                delta = cho_solve(cho_factor(H+damping*np.diag(diag)), g).reshape(3, d)
                trial = T-delta
                new_loss = objective(trial)
                if new_loss < loss:
                    T = trial
                    damping = max(1e-12, damping*.25)
                    accepted = True
                    break
                damping *= 5
            if not accepted or np.max(np.abs(delta)) < config['step_tolerance']:
                break
        final_loss = objective(T)
        traces.append(dict(start=start, iterations=iteration+1, loss=final_loss,
                           gradient_max=float(np.max(np.abs(objective(T, True)[1])))))
        if best is None or final_loss < best[0]:
            best = (final_loss, T.copy())
    beta = solve_triangular(R, best[1].T).T
    return beta, traces


def analyse(data, config):
    D = load_data(data)
    cal = calibration(D)
    X = features(D['bits'])
    output, diagnostics = [], []
    for protein in D['meta']['proteins']:
        train, n, k = protein_arrays(D, protein)
        m = slope(D['bits'], protein)
        beta, traces = fit_landscape(X[train], m[train], n, k,
                                     D['meta']['screen_conditions'], cal, config)
        energy = X@beta.T
        pa, _, _ = occupancy(energy, m, D['meta']['challenge_conditions'])
        apo = expit(-energy[:, 0])
        score = utility(apo, pa, D['bits'], D['meta'])
        index = int(np.argmax(score))
        output.append(dict(id=protein['id'], energy=energy.tolist(), apo_folded=apo.tolist(),
                           challenge_a=pa.tolist(), selected_variant=D['rows'][index]['variant_id']))
        diagnostics.append(dict(id=protein['id'], optimizer_starts=traces,
                                coefficients=beta.tolist(), selected_utility=float(score[index])))
    return dict(schema='thermodynamic_design/1', case_id=D['meta']['case_id'],
                calibration=cal, proteins=output), diagnostics, D
