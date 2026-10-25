import argparse,csv,json,hashlib,itertools,math
from pathlib import Path

def validate(data):
 d=Path(data);read=lambda n:json.loads((d/(n+'.json')).read_text())
 for name,v in read('data_manifest')['files'].items():
  raw=(d/name).read_bytes();assert len(raw)==v['bytes'] and hashlib.sha256(raw).hexdigest()==v['sha256'],name+' hash mismatch'
 cs=read('contexts');ps=read('policies')
 with (d/'tables.csv').open() as stream:rows=list(csv.DictReader(stream))
 assert len(cs)==3 and len({c['id'] for c in cs})==3
 assert len(ps)==24 and len({p['id'] for p in ps})==24
 for p in ps+[read('benchmark')]:
  assert len(p['a'])==2 and len(p['b'])==2 and all(len(r)==2 for r in p['b']);assert all(x in [0,1] for x in p['a']+[x for r in p['b'] for x in r])
 protocols=['natural','priming_trial','rescue_trial','sequential_trial'];seen=set();groups={}
 contexts={c['id']:c for c in cs}
 for c in cs:
  assert all(0<c[k]<1 for k in ['z_false_positive','z_false_negative','image_flip','target_x1'])
  assert c['z_false_positive']+c['z_false_negative']<1 and c['image_flip']<.5
  assert c['rescue_cost']>0 and 0<c['probability_band']<.001
  assert len(c['labs'])==2 and len({l['id'] for l in c['labs']})==2 and all(0<l['x1']<1 for l in c['labs'])
 for row in rows:
  cid=row['context'];assert cid in contexts and row['lab'] in {l['id'] for l in contexts[cid]['labs']} and row['protocol'] in protocols
  bits=tuple(int(row[k]) for k in ['Z','A','W','B','S']);assert all(v in [0,1] for v in bits)
  assert (bits[-1]==0 and row['Y']=='NA') or (bits[-1]==1 and row['Y'] in ['0','1'])
  key=(cid,row['lab'],row['protocol'],*bits,row['Y']);assert key not in seen;seen.add(key)
  p=float(row['probability']);assert math.isfinite(p) and 0<=p<=1
  groups.setdefault((cid,row['lab'],row['protocol']),[]).append(p)
 assert len(rows)==1152 and len(groups)==24 and all(len(v)==48 and abs(sum(v)-1)<1e-9 for v in groups.values())
 for f in ['deliverables.json','required_deliverables.json']:
  if (d.parent/f).exists():assert json.loads((d.parent/f).read_text())==['run_pipeline.py','final_answer.json','analysis.md']
 return {'status':'success','contexts':len(cs),'policies':len(ps),'table_rows':len(rows),'required_slots':['run_pipeline.py','final_answer.json','analysis.md']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();print(json.dumps(validate(a.data)))
