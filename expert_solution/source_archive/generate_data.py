"""Deterministic synthetic carbon-equivalent network and calibrated assay generator."""
from pathlib import Path
import json, hashlib
import numpy as np
from scipy.optimize import linprog
ROOT=Path(__file__).resolve().parents[2]
def write(p,o): p.write_text(json.dumps(o,indent=2,allow_nan=False)+'\n')
def generate(root=ROOT):
 d=root/'task/data';d.mkdir(parents=True,exist_ok=True)
 rng=np.random.default_rng(814729)
 mets=['hexose_C','triose_C','pyruvate_C','acetyl_C','TCA_C','precursor_C','NADH','NADPH','ATP']
 rows=[('glucose_import',{0:1}),('hexose_activation',{0:-1,1:1,8:-.2}),('glycolysis',{1:-1,2:1,6:.5,8:1}),('PDH',{2:-1,3:.67,6:.33}),('TCA_entry',{3:-1,4:1,6:.6,8:.2}),('precursor_synthesis',{4:-1,5:1,8:-.1}),('anaplerosis',{2:-1,4:1,8:-.3}),('biomass',{5:-1,8:-1,7:-.5}),('acetate_export',{3:-1,8:.3}),('lactate_export',{2:-1,6:-.5}),('ethanol_export',{3:-1,6:-.7}),('respiration',{6:-1,8:2}),('ATP_maintenance',{8:-1}),('oxidative_PPP',{0:-1,5:1,7:.8}),('malic_shunt',{4:-1,2:1,7:.4}),('transhydrogenase',{6:-1,7:1,8:-.2}),('NADPH_drain',{7:-1}),('hexose_precursor',{0:-1,5:1,8:-.2}),('precursor_export',{5:-1}),('alternative_respiration',{6:-1,8:.8}),('triose_import',{1:1}),('pyruvate_import',{2:1}),('isomerase_forward',{0:-1,1:1}),('isomerase_reverse',{1:-1,0:1}),('precursor_exchange_forward',{4:-1,5:1}),('precursor_exchange_reverse',{5:-1,4:1}),('reverse_transhydrogenase',{7:-1,6:1}),('NADPH_respiration',{7:-1,8:1.4}),('glyoxylate_shunt',{3:-1,5:1}),('TCA_export',{4:-1}),('pyruvate_export',{2:-1}),('photophosphorylation',{8:1})]
 S=np.zeros((len(mets),len(rows)))
 for j,(_,x) in enumerate(rows):
  for i,v in x.items(): S[i,j]=v
 write(d/'network.json',{'metabolites':mets,'reactions':[r[0] for r in rows],'stoichiometry':S.tolist()})
 modules=[]
 for group in ['uptake','redox','export']:
  for j in range(3):
   modules.append({'id':f'{group}_{j+1}','group':group,'cost':[2,3,4][j]})
 design={'modules':modules,'choose_per_group':1,'budget':10,'incompatible_pairs':[['uptake_1','redox_3'],['redox_1','export_3']],'safety_floor':9.0}
 write(d/'design_rules.json',design)
 # Main assay columns observe net exchange, not both directions of cycles.
 H=rng.normal(0,.1,(28,32))
 H[:10]=0
 for k,j in enumerate([0,7,8,9,10,11,13,18,20,21]):H[k,j]=1
 H[:,22]=H[:,1];H[:,23]=-H[:,1]
 H[:,24]=H[:,5];H[:,25]=-H[:,5]
 # Formally these are a calibrated linear tracer/flux fingerprint, not raw MID fractions.
 write(d/'assay_panel.json',{'channels':[f'F{i+1:02d}' for i in range(28)],'H':H.tolist(),'offset_groups':[i%4 for i in range(28)]})
 contexts=[];truth={}
 for k in range(8):
  cid=f'culture_{k+1:02d}'
  bounds=np.tile([0.,16.],(32,1));bounds[0]=[8+.45*k,8+.45*k];bounds[7]=[1.0,9];bounds[12]=[.8,12];bounds[20]=[0,2];bounds[21]=[0,1.5];bounds[31]=[0,0]
  # Capacity changes represent eight distinct steady-state media.
  bounds[11,1]=3+.4*k;bounds[13,1]=3.8+.2*(7-k)
  verts=[]
  for _ in range(18):
   r=linprog(rng.normal(size=32),A_eq=S,b_eq=np.zeros(9),bounds=bounds,method='highs')
   assert r.success;verts.append(r.x)
  v=np.mean(verts,axis=0);b=rng.uniform(-.3,.3,4)
  observations=[];standards=[]
  for j in range(28):
   eps=.07 if j<10 else .12
   y=float(H[j]@v+b[j%4]+rng.uniform(-eps*.3,eps*.3))
   observations.append({'channel':f'F{j+1:02d}','value':y,'halfwidth':eps})
  for j in range(4):
   for rep in range(3):
    known=float(1+rep*.8)
    standards.append({'id':f'S{j}_{rep}','offset_group':j,'known':known,'observed':known+float(b[j]+rng.uniform(-.018,.018)),'halfwidth':.08})
  # All response surfaces are coefficients from a stipulated first-order intervention model.
  # Deliberate context dependence prevents an exchangeable average-medium answer.
  base=rng.normal(0,.26,32)
  response={'baseline_intercept':float(rng.uniform(31,33)),'baseline_coefficients':base.tolist(),'modules':{}}
  shared=rng.normal(0,.16,32)
  for m in modules:
   coeff=rng.normal(0,.22,32)+shared
   coeff[[22,23,24,25]]=0 # utilities concern net processes, not invisible gross cycles
   response['modules'][m['id']]={'intercept':float(rng.uniform(.2,1.2)),'coefficients':coeff.tolist()}
  # Paired antagonistic responses with known positive rescue in some contexts.
  contexts.append({'id':cid,'bounds':bounds.tolist(),'offset_bounds':[[-.6,.6]]*4,'observations':observations,'standards':standards,'response':response})
  truth[cid]={'flux':v.tolist(),'offset':b.tolist()}
 write(d/'cultures.json',contexts)
 meta={'case_id':'ALS_FLUX_RESCUE_001','schema':'flux_rescue/1','units':{'flux':'mmol carbon-equivalent / gDW / hour','utility':'dimensionless rescue index'},'acceptance':{'numeric_abs':0.002,'witness_feasibility_abs':0.00002,'witness_objective_abs':0.002,'selection_regret_slack':0.002,'identifiable_width':0.01},'tie_tolerance':1e-7}
 write(d/'study_metadata.json',meta)
 write(root/'expert_solution/private/generation_truth.json',truth)
 write(d/'source_provenance.json',{'origin':'Entirely synthetic methods-study data','generator':'expert_solution/source_archive/generate_data.py','seed':814729,'measurement_model':'Bounded-error calibrated linear tracer-flux fingerprints with shared additive offset per group; not raw isotope mass-isotopomer distributions.','biological_scope':'Reduced carbon-equivalent network; reaction stoichiometry is the complete stipulated model, with no claim of atom mapping or clinical validity.','rights':'Original generated data released under CC0-1.0. Code released under MIT; see SOURCE_RIGHTS.md.'})
 files=['network.json','assay_panel.json','cultures.json','design_rules.json','study_metadata.json','source_provenance.json']
 write(d/'data_manifest.json',{'files':{f:{'bytes':(d/f).stat().st_size,'sha256':hashlib.sha256((d/f).read_bytes()).hexdigest()} for f in files}})
if __name__=='__main__':generate()
