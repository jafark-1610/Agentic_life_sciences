"""Calculated witness diagnostics and answer serialization."""
import json
from pathlib import Path
import numpy as np
from kinetics import generator, observable, moments, candidate_statistics


def round_values(obj):
    if isinstance(obj, float): return round(obj, 8)
    if isinstance(obj, list): return [round_values(v) for v in obj]
    if isinstance(obj, dict): return {k: round_values(v) for k, v in obj.items()}
    return obj


def evidence(answer, D):
    rows = {p['id']: p for p in answer['preparations']}; output = []
    meta = D['meta']; policy_indices = {p['id']: i for i, p in enumerate(meta['policies'])}
    for panel in D['panels']:
        obj = rows[panel['id']]; weights = np.array(obj['mixture_weights'])
        index = policy_indices[obj['selected_policy']]; calculated = {}
        for side in ['lower', 'upper']:
            families = [dict(exchange=np.array(R), models=np.array([fb]))
                        for R, fb in zip(obj['exchange_generators'], obj['net_witnesses'][side])]
            stats = [candidate_statistics(f, panel['protocol'], meta['policies']) for f in families]
            den = sum(w*s['d'][0] for w, s in zip(weights, stats))
            net = sum(w*s['net'][0, index] for w, s in zip(weights, stats))/den
            calculated[side+'_net_witness_value'] = float(net)
            calculated[side+'_selection_probability'] = float(den)
            if side == 'lower':
                A = np.array([observable(generator(f['exchange'], f['models'][0]), panel['arrays']['response'], meta['frame_time']) for f in families]).T
                _, two, three = moments(A, weights)
                calculated['moment2_max_abs_error'] = float(np.max(np.abs(two-panel['arrays']['moment2'])))
                calculated['moment3_max_abs_error'] = float(np.max(np.abs(three-panel['arrays']['moment3'])))
        output.append(dict(id=panel['id'], **calculated))
    return output


def write_outputs(answer, D, out, method=None):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); answer = round_values(answer)
    (out/'final_answer.json').write_text(json.dumps(answer, separators=(',', ':'), allow_nan=False)+'\n')
    diagnostics = round_values(evidence(answer, D))
    method = method or ('The persistent subtype distributions are separated using the three-view population tensor. '
                        'Each compatible continuous-time generator is retained. Conditional bounds optimize one '
                        'fixed microscopic generator per subtype jointly across screening, observation branches, '
             'intervention and benchmark. The shared bulk-turnover calibration is enforced on complete '
             'preparation models. First-passage probabilities use competing absorbing events.')
    text = '# Persistent-cycle intervention analysis\n\n'+method+'\n\n'
    text += 'The following numbers are computed from the serialized witness rates, exchange generators, mixture weights, and public protocol.\n\n```json\n'
    text += json.dumps({'preparations': diagnostics}, indent=2)+'\n```\n\n'
    text += ('The observations identify discrete-time transition laws. A microscopic rate or intervention value '
             'is reported as an interval whenever more than one compatible continuous-time model remains. '
             'The preparation subtypes persist through the entire protocol. These are simulated population '
             'readouts and nonequilibrium kinetic models; conclusions apply only to the stated model family.\n')
    (out/'analysis.md').write_text(text)
    return answer
