"""Validate input hashes, every count, and all cross-file keys."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def validate(data):
    data = Path(data)
    meta = json.loads((data/'study_metadata.json').read_text())
    manifest = json.loads((data/'data_manifest.json').read_text())
    for name, info in manifest['files'].items():
        raw = (data/name).read_bytes()
        assert len(raw) == info['bytes'] and hashlib.sha256(raw).hexdigest() == info['sha256'], name+' integrity mismatch'
    assert meta['case_id'] == 'ALS_THERMODYNAMIC_DESIGN_004'
    with (data/'variants.csv').open() as f:
        reader = csv.DictReader(f); assert reader.fieldnames == ['variant_id', 'mutations', 'role']; rows = list(reader)
    assert len(rows) == meta['n_variants']
    ids, screen = set(), set()
    for r in rows:
        assert r['variant_id'] not in ids
        ids.add(r['variant_id'])
        assert len(r['mutations']) == len(meta['positions']) and set(r['mutations']) <= {'0', '1'}
        code = sum(int(b) << i for i, b in enumerate(r['mutations']))
        assert r['variant_id'] == 'v'+format(code, '05x')
        assert r['role'] in ['screen', 'candidate']
        if r['role'] == 'screen': screen.add(r['variant_id'])
    assert len(screen) == meta['n_screen']
    proteins = {p['id'] for p in meta['proteins']}
    assert len(proteins) == len(meta['proteins'])
    for p in meta['proteins']:
        assert p['m0']-sum(abs(x) for x in p['mutation_m_shift']) > 0
        assert len(p['mutation_m_shift']) == len(meta['positions'])
    conditions = {c['id'] for c in meta['screen_conditions']}
    assert len(conditions) == len(meta['screen_conditions'])
    for c in meta['screen_conditions']:
        assert c['reporter'] in ['A', 'B']
        assert c['ligand_a' if c['reporter'] == 'A' else 'ligand_b'] > 0
        assert c['ligand_b' if c['reporter'] == 'A' else 'ligand_a'] == 0
    seen = set()
    with (data/'capture_counts.csv').open() as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['protein_id', 'variant_id', 'condition_id', 'trials', 'captured']
        for r in reader:
            key = r['protein_id'], r['variant_id'], r['condition_id']
            assert key not in seen and key[0] in proteins and key[1] in screen and key[2] in conditions
            seen.add(key)
            n, k = int(r['trials']), int(r['captured']); assert n > 0 and 0 <= k <= n
    assert len(seen) == len(proteins)*len(screen)*len(conditions)
    seen = set(); control_fractions = {c: set() for c in conditions}
    with (data/'calibration_counts.csv').open() as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['condition_id', 'control_id', 'bound_fraction', 'trials', 'captured']
        for r in reader:
            key = r['condition_id'], r['control_id']
            assert key not in seen and key[0] in conditions
            seen.add(key)
            n, k = int(r['trials']), int(r['captured']); t = float(r['bound_fraction'])
            assert n > 0 and 0 <= k <= n and 0 <= t <= 1
            control_fractions[key[0]].add(t)
    assert all(0 in t and 1 in t and len(t) >= 3 for t in control_fractions.values())
    assert len({c['id'] for c in meta['challenge_conditions']}) == len(meta['challenge_conditions'])
    for c in meta['challenge_conditions']:
        assert c['ligand_a'] > 0 and c['ligand_b'] > 0
        assert meta['urea_baseline_molar']+c['urea'] >= 0
    print('Input validation passed: complete variants, assays, calibration controls and integrity manifest.')
    return True


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--data', type=Path, default=Path(__file__).resolve().parent)
    validate(p.parse_args().data)
