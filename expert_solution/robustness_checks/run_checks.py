"""Scientific invariance and baseline checks; no solver trial outcomes are fabricated."""
import sys,json,copy
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parent;sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'tests'))
from expert_solution import load,polytope,solve,utility,portfolios
from score_rubric import grade,read_strict
from independent_oracle import verify,matrix,opt,response

def run():
 data=ROOT/'task/data';D=load(data);ref=read_strict(HERE/'final_answer.json');plans=portfolios(D['design_rules']);acc=D['study_metadata']['acceptance'];records=[]
 def record(name,observed,criterion,ok):records.append({'check':name,'observed':observed,'criterion':criterion,'status':'pass' if ok else 'fail'})
 result=verify(data,ref);record('independent_matrix_assembly_and_dual_certificates',result,'every computed endpoint and regret agrees within 1e-6',result['maximum_absolute_error']<1e-6)
 # Full support functions for selected/challenger objectives cover the decision, not just feasibility.
 maxdiff={'input_order':0.,'calibration_origin':0.,'flux_unit':0.}
 for c in D['cultures']:
  model=matrix(D['network'],D['assay_panel'],c)
  changed=copy.deepcopy(c);changed['observations'].reverse();changed['standards'].reverse();order=matrix(D['network'],D['assay_panel'],changed)
  shifted=copy.deepcopy(c);delta=np.array([.17,-.21,.09,.13]);groups=dict(zip(D['assay_panel']['channels'],D['assay_panel']['offset_groups']))
  for o in shifted['observations']:o['value']+=float(delta[groups[o['channel']]])
  for o in shifted['standards']:o['observed']+=float(delta[o['offset_group']])
  shifted['offset_bounds']=[[lo+delta[i],hi+delta[i]] for i,(lo,hi) in enumerate(c['offset_bounds'])]
  shift=matrix(D['network'],D['assay_panel'],shifted)
  unit=copy.deepcopy(c);panel=copy.deepcopy(D['assay_panel']);factor=7.
  unit['bounds']=(np.array(c['bounds'])*factor).tolist();panel['H']=(np.array(panel['H'])/factor).tolist();rescale=matrix(D['network'],panel,unit)
  chosen=ref['selection']['modules'];a,v=utility(c,chosen)
  for p in plans:
   aa,vv=utility(c,p);obj=vv-v;base,_=opt(model,obj,True)
   for name,m,ob in [('input_order',order,obj),('calibration_origin',shift,obj),('flux_unit',rescale,np.r_[obj[:32]/factor,obj[32:]])]:
    value,_=opt(m,ob,True);maxdiff[name]=max(maxdiff[name],abs(base-value))
 for name,val in maxdiff.items():record(name,{'max_support_difference':val},'maximum support difference < 1e-6',val<1e-6)
 # Center of feasible LP extrema: all assay checks pass, but it is not the regret target.
 point_floor={p:float('inf') for p in plans};point_regret={p:0. for p in plans};box_floor={p:float('inf') for p in plans};box_regret={p:0. for p in plans};point_violation=0.
 rangeby={c['id']:c['flux_ranges'] for c in ref['cultures']}
 for c in D['cultures']:
  P=polytope(D,c);vertices=[]
  for j in range(32):
   e=np.eye(36)[j]
   vertices += [solve(P,e)[1],solve(P,-e)[1]]
  point=np.mean(vertices,axis=0);point_violation=max(point_violation,float(np.max(P['A_ub']@point-P['b_ub'])),float(np.max(np.abs(P['A_eq']@point))))
  scores={p:utility(c,p)[0]+utility(c,p)[1]@point for p in plans};best=max(scores.values())
  lo=np.array([r['lower'] for r in rangeby[c['id']]]);hi=np.array([r['upper'] for r in rangeby[c['id']]])
  for p in plans:
   point_floor[p]=min(point_floor[p],scores[p]);point_regret[p]=max(point_regret[p],best-scores[p]);a,v=utility(c,p);v=v[:32]
   box_floor[p]=min(box_floor[p],a+np.minimum(v*lo,v*hi).sum())
   for q in plans:
    aa,vv=utility(c,q);diff=vv[:32]-v;gap=aa-a+np.maximum(diff*lo,diff*hi).sum();box_regret[p]=max(box_regret[p],gap)
 def decide(floors,regrets):
  safe=[p for p in plans if floors[p]>=D['design_rules']['safety_floor']]
  return list(min(safe,key=lambda p:(regrets[p],p))) if safe else []
 baseline={'feasible_point':decide(point_floor,point_regret),'marginal_box':decide(box_floor,box_regret)}
 safe=[d for d in ref['designs'] if d['floor']>=D['design_rules']['safety_floor']];baseline['maximin_utility']=min(safe,key=lambda d:(-d['floor'],tuple(d['modules'])))['modules']
 winner=ref['selection']['modules'];lookup={tuple(d['modules']):d for d in ref['designs']};best=lookup[tuple(winner)]['regret']
 for name,p in baseline.items():
  actual=lookup.get(tuple(p));acceptable=bool(actual and actual['floor']>=D['design_rules']['safety_floor'] and actual['regret']<=best+acc['selection_regret_slack'])
  record('baseline_'+name,{'selected':p,'accepted_decision':acceptable,'true_metrics':actual,'point_max_constraint_violation':point_violation if name=='feasible_point' else None},'baseline must fail the scientific decision to demonstrate a meaningful method distinction',not acceptable)
 # Reference gate clearance: residual error vs allowed error and winner vs runner-up.
 g=grade(ref,data);residual=max(g['details'].get('witness_violation',0.),0.);next_regret=min(d['regret'] for d in safe if d['modules']!=winner);margin=next_regret-best;safety_margin=lookup[tuple(winner)]['floor']-D['design_rules']['safety_floor']
 record('reference_gate_clearance',{'witness_violation':residual,'decision_margin':margin,'safety_margin':safety_margin,'witness_tolerance':acc['witness_feasibility_abs'],'selection_slack':acc['selection_regret_slack']},'witness error <= tolerance/3 and decision and safety margins >= 3*selection slack',residual<=acc['witness_feasibility_abs']/3 and margin>=3*acc['selection_regret_slack'] and safety_margin>=3*acc['selection_regret_slack'])
 altered=copy.deepcopy(ref);altered['selection']['witness']['flux'][0]+=1;r=grade(altered,data)
 record('changed_witness_rejected',{'score':r['final_score'],'checks':r['checks']},'infeasible witness fails scientific gate',not r['passed'] and not r['checks']['adversarial_witness'])
 result={'role':'local_scientific_robustness_not_model_runs','status':'pass' if all(r['status']=='pass' for r in records) else 'fail','checks':records}
 out=Path(__file__).resolve().parent;(out/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');(out/'result.md').write_text('# Robustness results\n\n'+'\n'.join(f"* {r['check']}: {r['status']}. {r['criterion']}. Observed: {json.dumps(r['observed'])}" for r in records)+'\n');print(json.dumps({'status':result['status'],'checks':[(r['check'],r['status']) for r in records]},indent=2));return 0 if result['status']=='pass' else 1
if __name__=='__main__':sys.exit(run())
