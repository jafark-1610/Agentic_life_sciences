import json,hashlib,argparse,math
from pathlib import Path

def check(data):
 d=Path(data);j=lambda f:json.loads((d/(f+'.json')).read_text())
 for name,v in j('data_manifest')['files'].items():
  b=(d/name).read_bytes();assert hashlib.sha256(b).hexdigest()==v['sha256'] and len(b)==v['bytes'],name
 spec=j('model_spec');chips=j('chips');ps=j('protocols');courses=j('courses');sc=j('scenarios')
 assert len(spec['parameters'])==10 and len(spec['parameter_bounds'])==10
 assert all(0<lo<hi for lo,hi in spec['parameter_bounds'])
 assert len(chips)==6 and len({c['id'] for c in chips})==6
 assert len(courses)==48 and len({c['id'] for c in courses})==48
 assert len(ps)==3 and len(sc)==3
 for p in ps+courses:
  assert p['horizon']>0 and all(0<=t<p['horizon'] and dose>0 for t,dose in p['pulses'])
  assert len({t for t,d in p['pulses']})==len(p['pulses'])
  assert all(0<=w['start']<w['end']<=p['horizon'] and w['strength']>=0 and w['site'] in ['site1','both'] for w in p['blockade'])
 for c in chips:
  assert c['known']['kint1']==c['known']['kint2'] and min(c['known'].values())>0
  seen=set()
  for o in c['observations']:
   assert o['protocol'] in {p['id'] for p in ps} and o['channel'] in spec['channels']
   assert 0<=o['time']<=next(p['horizon'] for p in ps if p['id']==o['protocol'])
   assert math.isfinite(o['signal']);key=(o['protocol'],o['time'],o['channel']);assert key not in seen;seen.add(key)
  assert len(seen)==120
  for channel in spec['channels']:
   assert {o['concentration'] for o in c['standards'] if o['channel']==channel}==set(spec['standards'])
 for scenario in sc:
  assert set(scenario['multipliers'])<=set(spec['parameters']) and all(x>0 for x in scenario['multipliers'].values())
 return {'status':'success','chips':len(chips),'protocols':len(ps),'courses':len(courses),'observations':sum(len(c['observations']) for c in chips)}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();print(json.dumps(check(a.data)))
