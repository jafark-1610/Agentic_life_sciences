"""Infer persistent subtype kernels and optimize interventions across all cycle aliases."""
import numpy as np
from kinetics import load_data, decompose, compatible_family, candidate_statistics
from envelopes import joint_bounds, feasible_joint_indices


def analyse(data, config, decomposition=None, bound_function=None, endpoint=False, family_override=None, joint_builder=None):
    D = load_data(data); meta = D['meta']; output, telemetry = [], []
    decomposition = decomposition or decompose
    bound_function = bound_function or joint_bounds
    joint_builder = joint_builder or feasible_joint_indices
    for panel in D['panels']:
        if family_override:
            weights, families = family_override(panel, meta)
        else:
            weights, A = decomposition(panel['arrays'], meta['subtypes'], config['tensor_contraction'])
            families = compatible_family(weights, A, panel['arrays'], meta)
        stats = [candidate_statistics(f, panel['protocol'], meta['policies'], endpoint) for f in families]
        joint = joint_builder(stats, weights, panel['protocol']['bulk_turnover'])
        intervals, extremizers = {}, {}
        for metric in ['success', 'loss', 'cost', 'gain', 'net']:
            interval, lo, hi = bound_function(stats, weights, metric, joint=joint)
            intervals[metric] = interval
            extremizers[metric] = (lo, hi)
        entropy, _, _ = bound_function(stats, weights, 'retained_epr', joint=joint)
        retention, _, _ = bound_function(stats, weights, 'retention', joint=joint)
        support = [np.unique(joint[:, h]) for h in range(meta['subtypes'])]
        selected = int(np.argmax(intervals['net'][:, 0]))
        policy_rows = [dict(id=p['id'], **{metric+'_bounds': intervals[metric][i].tolist() for metric in intervals})
                       for i, p in enumerate(meta['policies'])]
        witnesses = {}
        for side, ix in zip(['lower', 'upper'], extremizers['net']):
            witnesses[side] = [family['models'][int(ix[selected, h])].tolist() for h, family in enumerate(families)]
        output.append(dict(id=panel['id'], mixture_weights=weights.tolist(),
                           exchange_generators=[f['exchange'].tolist() for f in families],
                           forward_bounds=[np.column_stack([f['models'][support[h], :, 0].min(axis=0), f['models'][support[h], :, 0].max(axis=0)]).tolist() for h, f in enumerate(families)],
                           backward_bounds=[np.column_stack([f['models'][support[h], :, 1].min(axis=0), f['models'][support[h], :, 1].max(axis=0)]).tolist() for h, f in enumerate(families)],
                           candidate_counts=[len(f['models']) for f in families],
                           retention_bounds=retention[0].tolist(), retained_epr_bounds=entropy[0].tolist(),
                           policies=policy_rows, selected_policy=meta['policies'][selected]['id'],
                           net_witnesses=witnesses))
        telemetry.append(dict(id=panel['id'], candidate_counts=[len(f['models']) for f in families],
                              unconstrained_joint_count=int(np.prod([len(f['models']) for f in families])),
                              calibrated_joint_count=len(joint),
                              selected_index=selected, selected_lower_net=float(intervals['net'][selected, 0])))
    return dict(schema='persistent_cycle/1', case_id=meta['case_id'], preparations=output), D, telemetry
