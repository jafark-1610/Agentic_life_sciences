"""Explicit weaker estimators, scored as controls rather than model attempts."""
import numpy as np
from scipy.special import expit
from scipy.optimize import minimize_scalar
from model import features, slope, protein_arrays, calibration, occupancy, utility, deviance


def two_stage(D):
    X = features(D['bits']); cal = calibration(D); output, diagnostics = [], []
    bg = np.array([c['background'] for c in cal]); amp = np.array([c['ceiling']-c['background'] for c in cal])
    co = D['meta']['screen_conditions']
    u = np.array([c['urea'] for c in co]); ligand = np.array([max(c['ligand_a'], c['ligand_b']) for c in co])
    species = np.array([c['reporter'] == 'B' for c in co])
    for protein in D['meta']['proteins']:
        train, n, k = protein_arrays(D, protein); m = slope(D['bits'], protein)
        y = k/n; p = np.clip((y-bg)/amp, 1e-7, 1-1e-7)
        h = np.log(ligand)-np.log(p/(1-p)); w = n*(amp*p*(1-p))**2/np.maximum(y*(1-y), 1e-8)
        mu = m[train, None]*u
        latent = []
        for i in range(len(train)):
            def profile(f):
                z = h[i]-np.logaddexp(0, f+mu[i]); result = 0.
                for s in [False, True]:
                    mask = species == s; average = np.sum(w[i, mask]*z[mask])/np.sum(w[i, mask])
                    result += np.sum(w[i, mask]*(z[mask]-average)**2)
                return result
            fit = minimize_scalar(profile, method='bounded', bounds=(-8, 22), options={'xatol': 1e-8})
            f = float(fit.x); z = h[i]-np.logaddexp(0, f+mu[i]); affinities = []
            for s in [False, True]:
                mask = species == s; affinities.append(float(np.sum(w[i, mask]*z[mask])/np.sum(w[i, mask])))
            latent.append([f, *affinities])
        latent = np.array(latent)
        pa, pb, _ = occupancy(latent, m[train], co)
        q = bg+amp*np.where(species, pb, pa)
        diagnostics.append(dict(id=protein['id'], measured_variant_deviance_per_observation=float(deviance(n, k, q).mean()),
                                measured_variant_capture_rmse=float(np.sqrt(np.mean((q-y)**2)))))
        # Fitting the second-stage sequence surface does not account for asymmetric latent-estimation uncertainty.
        coef = np.linalg.lstsq(X[train], latent, rcond=None)[0]
        en = X@coef; apo = expit(-en[:, 0])
        challenge = occupancy(en, m, D['meta']['challenge_conditions'])[0]
        score = utility(apo, challenge, D['bits'], D['meta'])
        selected = D['rows'][int(np.argmax(score))]['variant_id']
        output.append(dict(id=protein['id'], energy=en.tolist(), apo_folded=apo.tolist(), challenge_a=challenge.tolist(), selected_variant=selected))
    return dict(schema='thermodynamic_design/1', case_id=D['meta']['case_id'], calibration=cal, proteins=output), diagnostics
