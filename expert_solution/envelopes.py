"""Sharp conditional envelopes over jointly calibrated subtype candidate sets."""
import numpy as np


def feasible_joint_indices(statistics, weights, calibration):
    """Meet-in-the-middle join of the three finite subtype supports."""
    flux = [w*s['flux'] for w, s in zip(weights, statistics)]
    pair = (flux[0][:, None]+flux[1][None, :]).ravel()
    a = np.repeat(np.arange(len(flux[0])), len(flux[1]))
    b = np.tile(np.arange(len(flux[1])), len(flux[0]))
    order = np.argsort(flux[2]); values = flux[2][order]
    lo = np.searchsorted(values, calibration['lower']-pair, side='left')
    hi = np.searchsorted(values, calibration['upper']-pair, side='right')
    pieces = []
    for start in range(len(values)):
        mask = lo <= start
        mask &= start < hi
        if np.any(mask): pieces.append(np.column_stack([a[mask], b[mask], np.full(mask.sum(), order[start])]))
    assert pieces, 'No jointly calibrated microscopic model'
    return np.concatenate(pieces).astype(np.int32)


def joint_bounds(statistics, weights, metric, chunk_size=10000, joint=None):
    """Sharp fractional bounds over every jointly calibrated discrete model."""
    assert joint is not None
    width = 1 if metric == 'retention' else statistics[0][metric].shape[1]
    lo, hi = np.full(width, np.inf), np.full(width, -np.inf)
    il, ih = np.zeros((width, 3), dtype=int), np.zeros((width, 3), dtype=int)
    for start in range(0, len(joint), chunk_size):
        rows = joint[start:start+chunk_size]
        denominator = sum(w*s['d'][rows[:, h]] for h, (w, s) in enumerate(zip(weights, statistics)))
        if metric == 'retention': values = denominator[:, None]
        else:
            numerator = sum(w*s[metric][rows[:, h]] for h, (w, s) in enumerate(zip(weights, statistics)))
            values = numerator/denominator[:, None]
        i0, i1 = np.argmin(values, axis=0), np.argmax(values, axis=0)
        v0, v1 = values[i0, np.arange(width)], values[i1, np.arange(width)]
        improve = v0 < lo; lo[improve] = v0[improve]; il[improve] = rows[i0[improve]]
        improve = v1 > hi; hi[improve] = v1[improve]; ih[improve] = rows[i1[improve]]
    return np.column_stack([lo, hi]), il, ih
