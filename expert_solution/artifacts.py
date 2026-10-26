"""Portable numeric serialization and calculated report evidence."""
import json
from pathlib import Path
from model import evidence


def rounded(obj):
    if isinstance(obj, float):
        return round(obj, 7)
    if isinstance(obj, list):
        return [rounded(x) for x in obj]
    if isinstance(obj, dict):
        return {k: rounded(v) for k, v in obj.items()}
    return obj


def write_outputs(answer, D, out, method_description=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    answer = rounded(answer)
    (out/'final_answer.json').write_text(json.dumps(answer, separators=(',', ':'), allow_nan=False)+'\n')
    ev = rounded(evidence(answer, D))
    method_description = method_description or ('Capture controls calibrate the background and ceiling independently for each assay. '
            'The four-state partition model is fitted jointly to all screen counts using quadratic genotype energies.')
    text = ('# Protein design analysis\n\n'+method_description+' '
            'Predictions retain competitive ligand binding and the measured '
            'genotype dependence of denaturation. The selected variant maximizes the published '
            'manufacturing and occupancy utility over the supplied candidate panel.\n\n'
            'The following diagnostics are calculated from the serialized answer and staged counts.\n\n'
            '```json\n'+json.dumps({'proteins': ev}, indent=2)+'\n```\n\n'
            'The assays are synthetic equilibrium measurements. The genotype model restricts '
            'energies to second order; conclusions do not establish clinical efficacy, dynamics, '
            'or behavior outside the specified mutation panel and thermodynamic conditions. '
            'A low capture residual does not independently validate latent energies or extrapolated designs.\n')
    (out/'analysis.md').write_text(text)
    return answer
