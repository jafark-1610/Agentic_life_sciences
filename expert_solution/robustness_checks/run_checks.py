import json,sys,copy,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'tests'))
from expert_solution import load,summarize,observed_vector
from causal_model import poly,coefficients,observation,solve,mp,sp,yp,I,N,pz,REF
from score_rubric import strict_read,science
from independent_oracle import build,fractional_bisection,support

def run():
 data=HERE.parent/'task/data';D=load(data);ref=strict_read(HERE/'final_answer.json');truth=strict_read(HERE/'private/generation_laws.json');checks=[]
 def add(name,observed,criterion,ok):checks.append({'check':name,'observed':observed,'criterion':criterion,'status':'pass' if ok else 'fail'})
 selected=next(p for p in D['policies'] if p['id']==ref['selection']['policy']);largest=0.
 for c in D['contexts']:
  P,n,d=build(data,c['id'],selected);lo=fractional_bisection(P,n,d);hi=fractional_bisection(P,n,d,True);glo=support(P,d);ghi=-support(P,-d);row=next(p for ctx in ref['contexts'] if ctx['id']==c['id'] for p in ctx['policies'] if p['id']==selected['id']);largest=max(largest,abs(lo-row['net_gain_lower']),abs(hi-row['net_gain_upper']),abs(glo-row['eligibility_lower']),abs(ghi-row['eligibility_upper']))
 add('independent_family_assembly_and_fractional_bisection',{'max_bound_difference':largest},'independent enumeration and bisection agree within 0.0001',largest<.0001)
 # A single completely compatible law reproduces every assay table yet makes the wrong decision.
 point=copy.deepcopy(ref);max_residual=0.
 for c in D['contexts']:
  law=np.array(truth[c['id']]);P=poly(c,observed_vector(D,c));max_residual=max(max_residual,float(np.max(P['A_ub']@law-P['b_ub'])))
  out=next(x for x in point['contexts'] if x['id']==c['id'])
  for p in D['policies']:
   v=coefficients(c,p);g=float(v['eligibility']@law);n=float(v['gain']@law)/g;h=float(v['harm']@law)/g;cost=float(v['cost']@law)
   row=next(r for r in out['policies'] if r['id']==p['id']);row.update(eligibility_lower=g,eligibility_upper=g,net_gain_lower=n,net_gain_upper=n,harm_upper=h,cost_upper=cost,point_identified=True)
 point['global_policies'],point['selection']=summarize(D,point['contexts']);r=science(point,data)
 add('compatible_point_law_baseline',{'table_band_violation':max(0.,max_residual),'selected':point['selection'],'score':r['final_score'],'checks':r['checks']},'a perfectly compatible point-law decision differs from the sharp robust decision and fails',max_residual<=1e-9 and point['selection']!=ref['selection'] and not r['passed'])
 # An independent-world approximation can preserve every single-world marginal and the benchmark identity.
 independent=copy.deepcopy(ref)
 def marginals(c,p,law):
  survival=coefficients(c,p)['survival']@law;success=0.
  for x in [0,1]:
   for z in [0,1]:
    for e in [0,1]:
     wt=(c['target_x1'] if x else 1-c['target_x1'])*pz(c,x,z)*(c['image_flip'] if e else 1-c['image_flip']);a=p['a'][z];m=mp[:,a];w=m^e;b=np.asarray(p['b'][z])[w];value=sp[I,m,b]*yp[I,m,b];success+=wt*(value@law[x*N:(x+1)*N])
  return float(survival),float(success)
 for c in D['contexts']:
  law=np.array(truth[c['id']]);sr,yr=marginals(c,REF,law);out=next(ctx for ctx in independent['contexts'] if ctx['id']==c['id'])
  for p in D['policies']:
   sp_,yp_=marginals(c,p,law);g=sp_*sr;n=yp_/sp_-yr/sr;h=(1-yp_/sp_)*(yr/sr)
   if p['a']==REF['a'] and p['b']==REF['b']:g=sr;n=0.;h=0.
   row=next(x for x in out['policies'] if x['id']==p['id']);row.update(eligibility_lower=g,eligibility_upper=g,net_gain_lower=n,net_gain_upper=n,harm_upper=h,cost_upper=float(coefficients(c,p)['cost']@law),point_identified=True)
 independent['global_policies'],independent['selection']=summarize(D,independent['contexts']);ir=science(independent,data)
 add('independent_world_baseline',{'score':ir['final_score'],'checks':ir['checks'],'selected':independent['selection'],'single_world_marginals_used_exactly':True,'benchmark_identity_preserved':True},'marginal fit and benchmark identity do not validate independent-world paired-clone quantities; baseline must fail',not ir['passed'])
 # Numerator/denominator corner division is not sharp optimization of a conditional quantity.
 differences=[]
 for c in D['contexts']:
  P=poly(c,observed_vector(D,c));cr=next(x for x in ref['contexts'] if x['id']==c['id'])
  for p in [x for x in D['policies'] if x['id'] in ['policy_02','policy_08','policy_14']]:
   v=coefficients(c,p);nl=solve(P,v['gain'])[0];nu=-solve(P,-v['gain'])[0];row=next(r for r in cr['policies'] if r['id']==p['id']);glo=row['eligibility_lower'];ghi=row['eligibility_upper'];corners=[n/g for n in [nl,nu] for g in [glo,ghi]];differences.append({'context':c['id'],'policy':p['id'],'outer_lower':min(corners),'sharp_lower':row['net_gain_lower'],'outer_upper':max(corners),'sharp_upper':row['net_gain_upper'],'max_error':max(abs(min(corners)-row['net_gain_lower']),abs(max(corners)-row['net_gain_upper']))})
 maxerr=max(x['max_error'] for x in differences)
 add('conditional_ratio_outer_bound_audit',{'largest_endpoint_error':maxerr,'examples':differences,'separates_at_scoring_tolerance':maxerr>D['study_metadata']['acceptance']['numeric_absolute'],'counted_as_difficulty_evidence':False},'outer intervals contain sharp intervals within 0.0001; no method is rejected merely for using an accurate approximation',all(x['outer_lower']<=x['sharp_lower']+.0001 and x['outer_upper']>=x['sharp_upper']-.0001 for x in differences))
 rows={r['id']:r for r in ref['global_policies']};limits=D['study_metadata']['decision'];winner=rows[ref['selection']['policy']];safe=[r for r in rows.values() if r['worst_harm']<=limits['maximum_harm'] and r['worst_cost']<=limits['maximum_cost'] and r['minimum_eligibility']>=limits['minimum_eligibility']];runner=max(r['resource_adjusted_score'] for r in safe if r['id']!=winner['id']);gap=winner['resource_adjusted_score']-runner;acc=D['study_metadata']['acceptance']
 margins={'harm':limits['maximum_harm']-winner['worst_harm'],'cost':limits['maximum_cost']-winner['worst_cost'],'eligibility':winner['minimum_eligibility']-limits['minimum_eligibility'],'score_gap':gap}
 add('reference_gate_clearance',margins,'decision gap >= 3 policy-score tolerances; all feasibility margins >= 3 numeric tolerances',gap>=3*acc['policy_score_absolute'] and min(margins[k] for k in ['harm','cost','eligibility'])>=3*acc['numeric_absolute'])
 wrapped=science([ref],data);add('wrapper_recovery',{'score':wrapped['final_score'],'checks':wrapped['checks']},'wrapper keeps all science and receives presentation deduction only',wrapped['final_score']==95 and all(wrapped['checks'].values()))
 add('three_slot_contract',{'files':strict_read(data.parent/'required_deliverables.json'),'task_mentions_auxiliary_execution_file':any('run_summary' in p.read_text() for p in data.parent.rglob('*') if p.is_file())},'the task requests exactly the three existing submission slots',strict_read(data.parent/'required_deliverables.json')==['run_pipeline.py','final_answer.json','analysis.md'] and not any('run_summary' in p.read_text() for p in data.parent.rglob('*') if p.is_file()))
 result={'role':'scientific_robustness_and_wrong_method_controls_not_model_runs','status':'pass' if all(r['status']=='pass' for r in checks) else 'fail','checks':checks};out=HERE/'robustness_checks';(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');(out/'result.md').write_text('# Robustness evidence\n\n'+'\n'.join(f"* {c['check']}: {c['status']}. {c['criterion']}. Observed: {json.dumps(c['observed'])}" for c in checks)+'\n');print(json.dumps(result,indent=2));return 0 if result['status']=='pass' else 1
if __name__=='__main__':sys.exit(run())
