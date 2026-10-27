import json,hashlib
from pathlib import Path
import numpy as np
def validate(data):
 data=Path(data);m=json.loads((data/'study_metadata.json').read_text());manifest=json.loads((data/'data_manifest.json').read_text())
 for f,r in manifest['files'].items():
  raw=(data/f).read_bytes();assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
 with np.load(data/'hybridization.npz',allow_pickle=False) as z:
  assert z['observed'].shape==(600,6,2,9,2);assert np.all(z['observed'][np.isfinite(z['observed'])]>0)
  assert z['spike_observed'].shape==(6,2,9,2,2,2)
  for k in z.files:
   if k!='observed':assert np.isfinite(z[k]).all() and (z[k]>0).all()
  assert z['run_on'].shape==(6,2,8,2) and z['cell_counts'].shape==(6,2,9)
 assert len(set(m['genes']))==600 and len(m['stress_group'])==600
 return True
if __name__=='__main__':validate(Path(__file__).resolve().parent);print('Dataset valid')
