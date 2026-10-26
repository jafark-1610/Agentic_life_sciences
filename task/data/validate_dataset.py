"""Check every population array, protocol, foreign key, and integrity hash."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def validate(data):
    data = Path(data); meta = json.loads((data/'study_metadata.json').read_text())
    manifest = json.loads((data/'data_manifest.json').read_text())
    for name, info in manifest['files'].items():
        raw = (data/name).read_bytes()
        assert len(raw) == info['bytes'] and hashlib.sha256(raw).hexdigest() == info['sha256'], name+' integrity mismatch'
    assert meta['case_id'] == 'ALS_HIDDEN_CYCLE_005'
    n, m, rank, d = meta['states'], meta['modules'], meta['subtypes'], meta['outcome_dimension']
    assert n == 3*m and d == m*n and rank == 3 and meta['frame_time'] > 0
    protocols = json.loads((data/'protocols.json').read_text())
    assert set(protocols) == {p['id'] for p in meta['preparations']}
    for p in meta['preparations']:
        with np.load(data/p['file'], allow_pickle=False) as z:
            assert set(z.files) == {'moment1', 'moment2', 'moment3', 'response'}
            one, two, three, C = [z[k] for k in ['moment1', 'moment2', 'moment3', 'response']]
            assert one.shape == (d,) and two.shape == (d,d) and three.shape == (d,d,d) and C.shape == (n,n)
            assert all(np.isfinite(a).all() and a.min() >= 0 for a in [one,two,three,C])
            assert abs(one.sum()-1) < 1e-12 and np.max(np.abs(C.sum(axis=1)-1)) < 1e-12
            assert np.linalg.cond(C) < 20
            assert np.max(np.abs(two.sum(axis=1)-one)) < 1e-12
            assert np.max(np.abs(three.sum(axis=2)-two)) < 1e-12
            assert np.max(np.abs(two-two.T)) < 1e-12
            assert np.max(np.abs(three-three.transpose(1,0,2))) < 1e-12
            assert np.max(np.abs(three-three.transpose(0,2,1))) < 1e-12
            ev = np.linalg.eigvalsh(two)
            assert ev[-rank] > 1e-9 and abs(ev[-rank-1]) < 1e-12
        e = protocols[p['id']]
        rho=np.array(e['initial_distribution']); H=np.array(e['observation']); selection=np.array(e['selection_probability'])
        assert rho.shape == (n,) and rho.min() >= 0 and abs(rho.sum()-1) < 1e-12
        assert H.shape == (n,3) and H.min() >= 0 and np.max(np.abs(H.sum(axis=1)-1)) < 1e-12
        assert selection.shape == (n,) and selection.min() > 0 and selection.max() <= 1
        assert len(e['pre_loss_rate']) == n and min(e['pre_loss_rate']) >= 0
        assert e['screen_time'] > 0 and e['followup_time'] > 0
        assert len(set(e['target_states'])) == len(e['target_states']) and all(0 <= i < n for i in e['target_states'])
        assert e['bulk_turnover']['lower'] < e['bulk_turnover']['upper']
        for a in e['actions']:
            M=np.array(a['multiplier']); assert M.shape == (n,n) and np.isfinite(M).all() and M.min() >= 0
            assert len(a['loss_rate']) == n and min(a['loss_rate']) > 0 and a['resource_cost'] >= 0
    assert len({p['id'] for p in meta['policies']}) == len(meta['policies'])
    assert all(len(p['actions']) == 3 and all(0 <= a < 4 for a in p['actions']) for p in meta['policies'])
    print('Input validation passed: complete population tensors, consistent protocols, and pinned files.')
    return True


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--data', type=Path, default=Path(__file__).resolve().parent)
    validate(p.parse_args().data)
